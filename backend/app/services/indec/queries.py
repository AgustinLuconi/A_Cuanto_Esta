"""Consultas de lectura sobre indec_observations (solo lee la base propia)."""
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.indec_observation import IndecObservation
from app.schemas.indec import (
    ChildCost,
    ChildCostGroup,
    FoodVsWages,
    IndecOverview,
    LatestPoint,
    WholesaleVsRetail,
)

_IPC = "ipc_nacional"
_CANASTAS = "valorizacion_canastas_cba_cbt"
_SALARIOS = "indice_salarios"
_MAYORISTA = "sipm_precios_mayoristas"
_CRIANZA = "canasta-crianza"

# Clasificador esperado de cada serie del overview. Se fija para que, si un mismo
# código apareciera bajo dos clasificadores, no se elija uno al azar.
_CLS_IPC_GENERAL = "IPC"
_CLS_IPC_COICOP = "COICOP Argentina 2019"
_CLS_CANASTAS = "CBA y CBT"
_CLS_SALARIOS = "IS 2001"
_CLS_MAYORISTA = "CIIU3"
_SRC_MAYORISTA = "IPIM"          # precios internos mayoristas (IPP e IPIB comparten códigos)
_REGION_MAYORISTA = "Total del país"

# Tramos de edad de la canasta de crianza, en orden: (código en la serie, etiqueta)
_AGE_GROUPS = (
    ("men1", "Menor de 1 año"),
    ("1a3", "1 a 3 años"),
    ("4a5", "4 a 5 años"),
    ("6a12", "6 a 12 años"),
)


def get_series(
    db: Session,
    *,
    dataset: str,
    code: str | None = None,
    region: str | None = None,
    indicator: str | None = None,
    classifier: str | None = None,
    source_indicator: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 1000,
) -> list[IndecObservation]:
    """Observaciones de un dataset, filtradas, ordenadas por período ascendente."""
    query = db.query(IndecObservation).filter(IndecObservation.dataset == dataset)
    if code is not None:
        query = query.filter(IndecObservation.series_code == code)
    if region is not None:
        query = query.filter(IndecObservation.region == region)
    if indicator is not None:
        query = query.filter(IndecObservation.indicator_type == indicator)
    if classifier is not None:
        query = query.filter(IndecObservation.classifier == classifier)
    if source_indicator is not None:
        query = query.filter(IndecObservation.indicator == source_indicator)
    if date_from is not None:
        query = query.filter(IndecObservation.period >= date_from)
    if date_to is not None:
        query = query.filter(IndecObservation.period <= date_to)
    return query.order_by(IndecObservation.period.asc()).limit(limit).all()


def _rebased_pair(
    first: dict[date, float], second: dict[date, float], months: int
) -> tuple[list[str], list[float], list[float]] | None:
    """
    Toma los últimos `months` períodos presentes en AMBAS series y reescala cada una
    a base 100 en el primer período común (redondeado a 2 decimales). None si hay
    menos de 2 períodos comunes o si algún valor base es 0.
    """
    common = sorted(set(first) & set(second))[-months:]
    if len(common) < 2:
        return None
    start = common[0]
    if first[start] == 0 or second[start] == 0:
        return None  # no se puede reescalar a base 100 desde cero
    return (
        [p.strftime("%Y-%m") for p in common],
        [round(first[p] / first[start] * 100, 2) for p in common],
        [round(second[p] / second[start] * 100, 2) for p in common],
    )


def build_food_vs_wages(
    ipc: dict[date, float], wages: dict[date, float], months: int = 24
) -> FoodVsWages | None:
    """IPC Alimentos vs. salarios en base 100 (ver `_rebased_pair`)."""
    pair = _rebased_pair(ipc, wages, months)
    if pair is None:
        return None
    labels, ipc_values, wage_values = pair
    return FoodVsWages(labels=labels, ipc_alimentos=ipc_values, salarios=wage_values)


def build_wholesale_vs_retail(
    wholesale: dict[date, float], retail: dict[date, float], months: int = 24
) -> WholesaleVsRetail | None:
    """Mayorista de alimentos vs. IPC Alimentos al consumidor en base 100."""
    pair = _rebased_pair(wholesale, retail, months)
    if pair is None:
        return None
    labels, wholesale_values, retail_values = pair
    return WholesaleVsRetail(
        labels=labels, mayorista_alimentos=wholesale_values, ipc_alimentos=retail_values
    )


def _latest_point(
    db: Session, dataset: str, classifier: str, code: str, region: str, indicator: str
) -> LatestPoint | None:
    row = (
        db.query(IndecObservation)
        .filter(
            IndecObservation.dataset == dataset,
            IndecObservation.classifier == classifier,
            IndecObservation.series_code == code,
            IndecObservation.region == region,
            IndecObservation.indicator_type == indicator,
        )
        .order_by(IndecObservation.period.desc())
        .first()
    )
    if row is None:
        return None
    return LatestPoint(period=row.period, value=float(row.value))


def _as_dict(rows: list[IndecObservation]) -> dict[date, float]:
    return {r.period: float(r.value) for r in rows}


def _child_cost(db: Session) -> ChildCost | None:
    """Costo de crianza del último período, un grupo por tramo de edad con sus 3 valores."""
    latest = (
        db.query(func.max(IndecObservation.period))
        .filter(IndecObservation.dataset == _CRIANZA)
        .scalar()
    )
    if latest is None:
        return None
    rows = (
        db.query(IndecObservation)
        .filter(IndecObservation.dataset == _CRIANZA, IndecObservation.period == latest)
        .all()
    )
    values = {r.series_code: float(r.value) for r in rows}
    groups = [
        ChildCostGroup(
            label=label,
            bienes_servicios=values[f"bys_{key}"],
            cuidado=values[f"cuid_{key}"],
            total=values[f"tot_{key}"],
        )
        for key, label in _AGE_GROUPS
        if all(f"{c}_{key}" in values for c in ("bys", "cuid", "tot"))
    ]
    return ChildCost(period=latest, groups=groups) if groups else None


def get_overview(db: Session) -> IndecOverview:
    """Último valor de cada serie de la pantalla; sin datos, cada campo queda en None."""
    ipc_alimentos = get_series(
        db, dataset=_IPC, classifier=_CLS_IPC_COICOP, code="01",
        region="Nacional", indicator="Indice", limit=5000,
    )
    salarios = get_series(
        db, dataset=_SALARIOS, classifier=_CLS_SALARIOS, code="0",
        region="Nacional", indicator="Indice", limit=5000,
    )
    wholesale_food = get_series(
        db, dataset=_MAYORISTA, classifier=_CLS_MAYORISTA, code="15",
        region=_REGION_MAYORISTA, indicator="Indice", source_indicator=_SRC_MAYORISTA, limit=5000,
    )
    return IndecOverview(
        ipc_general_mensual=_latest_point(db, _IPC, _CLS_IPC_GENERAL, "0", "Nacional", "v_m"),
        ipc_general_interanual=_latest_point(db, _IPC, _CLS_IPC_GENERAL, "0", "Nacional", "v_ia"),
        ipc_alimentos_mensual=_latest_point(db, _IPC, _CLS_IPC_COICOP, "01", "Nacional", "v_m"),
        ipc_alimentos_interanual=_latest_point(db, _IPC, _CLS_IPC_COICOP, "01", "Nacional", "v_ia"),
        cba=_latest_point(db, _CANASTAS, _CLS_CANASTAS, "CBA", "GBA", "CBA"),
        cbt=_latest_point(db, _CANASTAS, _CLS_CANASTAS, "CBT", "GBA", "CBT"),
        ice=_latest_point(db, _CANASTAS, _CLS_CANASTAS, "ICE", "GBA", "ICE"),
        food_vs_wages=build_food_vs_wages(_as_dict(ipc_alimentos), _as_dict(salarios)),
        wholesale_vs_retail=build_wholesale_vs_retail(
            _as_dict(wholesale_food), _as_dict(ipc_alimentos)
        ),
        child_cost=_child_cost(db),
    )
