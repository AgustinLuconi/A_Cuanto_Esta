"""
Endpoints de Indicadores Económicos.

GET /api/v1/economic/context            — Contexto macroeconómico actual
GET /api/v1/economic/inflation/history  — Historial de inflación mensual o anual
"""
from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.economic_indicator import EconomicIndicator, IndicatorType
from app.schemas import economic as schemas_eco

router = APIRouter()

_CONTEXT_TYPES = [
    IndicatorType.INFLATION_MONTHLY,
    IndicatorType.INFLATION_YEARLY,
    IndicatorType.DOLLAR_BLUE,
    IndicatorType.DOLLAR_OFICIAL,
    IndicatorType.DOLLAR_MAYORISTA,
    IndicatorType.DOLLAR_MEP,
    IndicatorType.DOLLAR_CCL,
    IndicatorType.DOLLAR_CRIPTO,
    IndicatorType.DOLLAR_TARJETA,
    IndicatorType.UVA_INDEX,
    IndicatorType.PLAZO_FIJO_RATE,
    IndicatorType.RISK_COUNTRY,
]


def _prev_value(db: Session, indicator_type: IndicatorType, latest_rec) -> Decimal | None:
    """Devuelve el valor del registro inmediatamente anterior al más reciente."""
    if latest_rec is None:
        return None
    prev = (
        db.query(EconomicIndicator)
        .filter(
            EconomicIndicator.indicator_type == indicator_type,
            EconomicIndicator.date < latest_rec.date,
        )
        .order_by(EconomicIndicator.date.desc())
        .first()
    )
    return prev.value if prev else None


def _value_and_change(
    db: Session,
    latest: dict[IndicatorType, EconomicIndicator | None],
    indicator_type: IndicatorType,
) -> tuple[Decimal | None, Decimal | None]:
    """Valor actual y variación % vs. registro anterior para un indicador."""
    rec = latest[indicator_type]
    if rec is None:
        return None, None
    prev = _prev_value(db, indicator_type, rec)
    if prev is None or float(prev) == 0:
        return rec.value, None
    change = Decimal(str((float(rec.value) - float(prev)) / float(prev) * 100))
    return rec.value, change


@router.get("/context", response_model=schemas_eco.EconomicContext)
def get_economic_context(db: Session = Depends(get_db)):
    """
    Contexto macroeconómico actual.

    Devuelve el valor más reciente de cada indicador clave:
    inflación mensual/anual, dólar blue y oficial, índice UVA,
    tasa de plazo fijo y riesgo país.
    Los campos quedan en `null` si no hay datos para ese indicador.
    Incluye variaciones (pp para inflación, % para dólar) y acumulado anual.
    """
    latest = {t: EconomicIndicator.get_latest_value(db, t) for t in _CONTEXT_TYPES}

    def val(t: IndicatorType):
        rec = latest[t]
        return rec.value if rec else None

    # Variación inflación mensual (diferencia en pp vs. mes anterior)
    infl_rec = latest[IndicatorType.INFLATION_MONTHLY]
    infl_prev = _prev_value(db, IndicatorType.INFLATION_MONTHLY, infl_rec)
    if infl_rec and infl_prev is not None:
        inflation_monthly_change = Decimal(str(float(infl_rec.value) - float(infl_prev)))
    else:
        inflation_monthly_change = None

    dollar_blue, dollar_blue_change = _value_and_change(db, latest, IndicatorType.DOLLAR_BLUE)
    dollar_oficial, dollar_oficial_change = _value_and_change(db, latest, IndicatorType.DOLLAR_OFICIAL)
    dollar_mayorista, dollar_mayorista_change = _value_and_change(db, latest, IndicatorType.DOLLAR_MAYORISTA)
    dollar_mep, dollar_mep_change = _value_and_change(db, latest, IndicatorType.DOLLAR_MEP)
    dollar_ccl, dollar_ccl_change = _value_and_change(db, latest, IndicatorType.DOLLAR_CCL)
    dollar_cripto, dollar_cripto_change = _value_and_change(db, latest, IndicatorType.DOLLAR_CRIPTO)
    dollar_tarjeta, dollar_tarjeta_change = _value_and_change(db, latest, IndicatorType.DOLLAR_TARJETA)
    risk_country, risk_country_change = _value_and_change(db, latest, IndicatorType.RISK_COUNTRY)

    # Inflación acumulada año corriente (compuesta)
    current_year = date.today().year
    ytd_records = (
        db.query(EconomicIndicator)
        .filter(
            EconomicIndicator.indicator_type == IndicatorType.INFLATION_MONTHLY,
            EconomicIndicator.date >= date(current_year, 1, 1),
        )
        .order_by(EconomicIndicator.date.asc())
        .all()
    )
    if ytd_records:
        compound = Decimal("1")
        for rec in ytd_records:
            compound *= 1 + rec.value / 100
        inflation_ytd = (compound - 1) * 100
    else:
        inflation_ytd = None

    # Fecha más reciente entre todos los registros disponibles
    dates = [rec.date for rec in latest.values() if rec is not None]
    last_updated = (
        datetime.combine(max(dates), time.min) if dates else datetime.utcnow()
    )

    # Inflación interanual (últimos 12 meses)
    last_12m_cutoff = date.today() - relativedelta(months=12)
    last_12m_records = (
        db.query(EconomicIndicator)
        .filter(
            EconomicIndicator.indicator_type == IndicatorType.INFLATION_MONTHLY,
            EconomicIndicator.date >= last_12m_cutoff,
        )
        .order_by(EconomicIndicator.date.asc())
        .all()
    )
    inflation_yearly_val = val(IndicatorType.INFLATION_YEARLY)
    if not inflation_yearly_val and len(last_12m_records) >= 1:
        compound = Decimal("1")
        # Tomar como máximo los últimos 12 registros
        for rec in last_12m_records[-12:]:
            compound *= 1 + rec.value / 100
        inflation_yearly_val = (compound - 1) * 100

    return schemas_eco.EconomicContext(
        inflation_monthly=val(IndicatorType.INFLATION_MONTHLY),
        inflation_yearly=inflation_yearly_val,
        dollar_blue=dollar_blue,
        dollar_oficial=dollar_oficial,
        dollar_mayorista=dollar_mayorista,
        dollar_mep=dollar_mep,
        dollar_ccl=dollar_ccl,
        dollar_cripto=dollar_cripto,
        dollar_tarjeta=dollar_tarjeta,
        uva_index=val(IndicatorType.UVA_INDEX),
        plazo_fijo_rate=val(IndicatorType.PLAZO_FIJO_RATE),
        risk_country=risk_country,
        last_updated=last_updated,
        inflation_monthly_change=inflation_monthly_change,
        inflation_monthly_date=infl_rec.date if infl_rec else None,
        dollar_blue_change=dollar_blue_change,
        dollar_oficial_change=dollar_oficial_change,
        dollar_mayorista_change=dollar_mayorista_change,
        dollar_mep_change=dollar_mep_change,
        dollar_ccl_change=dollar_ccl_change,
        dollar_cripto_change=dollar_cripto_change,
        dollar_tarjeta_change=dollar_tarjeta_change,
        risk_country_change=risk_country_change,
        inflation_ytd=inflation_ytd,
    )


@router.get("/dollar/history")
def get_dollar_history(
    months: int = Query(default=6, ge=1, le=24, description="Últimos N meses de historial"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Historial de cotización del dólar (blue y oficial).

    Devuelve los datos en formato adecuado para gráficos de línea doble.
    Si no hay registros para un tipo, el array correspondiente queda vacío.
    """
    cutoff = date.today() - relativedelta(months=months)

    blue = (
        db.query(EconomicIndicator)
        .filter(
            EconomicIndicator.indicator_type == IndicatorType.DOLLAR_BLUE,
            EconomicIndicator.date >= cutoff,
        )
        .order_by(EconomicIndicator.date.asc())
        .all()
    )
    oficial = (
        db.query(EconomicIndicator)
        .filter(
            EconomicIndicator.indicator_type == IndicatorType.DOLLAR_OFICIAL,
            EconomicIndicator.date >= cutoff,
        )
        .order_by(EconomicIndicator.date.asc())
        .all()
    )

    all_dates = sorted(set(r.date for r in blue + oficial))
    labels = [d.strftime("%b") for d in all_dates]

    blue_by_date = {r.date: float(r.value) for r in blue}
    oficial_by_date = {r.date: float(r.value) for r in oficial}

    return {
        "labels": labels,
        "blue": [blue_by_date.get(d, 0.0) for d in all_dates],
        "oficial": [oficial_by_date.get(d, 0.0) for d in all_dates],
    }


@router.get("/inflation/history", response_model=list[schemas_eco.EconomicIndicator])
def get_inflation_history(
    months: int = Query(12, ge=1, le=120, description="Últimos N meses de historial"),
    type: Literal["monthly", "yearly"] = Query("monthly", description="monthly o yearly"),
    db: Session = Depends(get_db),
):
    """
    Historial de inflación.

    Devuelve los registros ordenados por fecha descendente.
    - `type=monthly`: inflación mensual (IPC mensual)
    - `type=yearly`: inflación interanual acumulada
    - `months`: ventana de tiempo (máximo 120 meses = 10 años)
    """
    indicator_type = (
        IndicatorType.INFLATION_MONTHLY if type == "monthly"
        else IndicatorType.INFLATION_YEARLY
    )
    cutoff = date.today() - relativedelta(months=months)

    return (
        db.query(EconomicIndicator)
        .filter(
            EconomicIndicator.indicator_type == indicator_type,
            EconomicIndicator.date >= cutoff,
        )
        .order_by(EconomicIndicator.date.desc())
        .all()
    )


@router.get("/risk-country/history", response_model=list[schemas_eco.EconomicIndicator])
def get_risk_country_history(
    months: int = Query(12, ge=1, le=360, description="Últimos N meses de historial"),
    db: Session = Depends(get_db),
):
    """
    Historial de riesgo país (EMBI+).

    Devuelve los registros ordenados por fecha descendente.
    - `months`: ventana de tiempo (máximo 360 meses = 30 años; hay datos desde 1999)
    """
    cutoff = date.today() - relativedelta(months=months)

    return (
        db.query(EconomicIndicator)
        .filter(
            EconomicIndicator.indicator_type == IndicatorType.RISK_COUNTRY,
            EconomicIndicator.date >= cutoff,
        )
        .order_by(EconomicIndicator.date.desc())
        .all()
    )
