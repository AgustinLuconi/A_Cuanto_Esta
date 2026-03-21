"""
Endpoints de Indicadores Económicos.

GET /api/v1/economic/context            — Contexto macroeconómico actual
GET /api/v1/economic/inflation/history  — Historial de inflación mensual o anual
"""
from datetime import date, datetime, time
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
    IndicatorType.UVA_INDEX,
    IndicatorType.PLAZO_FIJO_RATE,
    IndicatorType.RISK_COUNTRY,
]


@router.get("/context", response_model=schemas_eco.EconomicContext)
def get_economic_context(db: Session = Depends(get_db)):
    """
    Contexto macroeconómico actual.

    Devuelve el valor más reciente de cada indicador clave:
    inflación mensual/anual, dólar blue y oficial, índice UVA,
    tasa de plazo fijo y riesgo país.
    Los campos quedan en `null` si no hay datos para ese indicador.
    """
    latest = {t: EconomicIndicator.get_latest_value(db, t) for t in _CONTEXT_TYPES}

    def val(t: IndicatorType):
        rec = latest[t]
        return rec.value if rec else None

    # Fecha más reciente entre todos los registros disponibles
    dates = [rec.date for rec in latest.values() if rec is not None]
    last_updated = (
        datetime.combine(max(dates), time.min) if dates else datetime.utcnow()
    )

    return schemas_eco.EconomicContext(
        inflation_monthly=val(IndicatorType.INFLATION_MONTHLY),
        inflation_yearly=val(IndicatorType.INFLATION_YEARLY),
        dollar_blue=val(IndicatorType.DOLLAR_BLUE),
        dollar_oficial=val(IndicatorType.DOLLAR_OFICIAL),
        uva_index=val(IndicatorType.UVA_INDEX),
        plazo_fijo_rate=val(IndicatorType.PLAZO_FIJO_RATE),
        risk_country=val(IndicatorType.RISK_COUNTRY),
        last_updated=last_updated,
    )


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
