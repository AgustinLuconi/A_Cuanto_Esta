"""Consultas de lectura sobre indec_observations (solo lee la base propia)."""
from datetime import date

from sqlalchemy.orm import Session

from app.models.indec_observation import IndecObservation
from app.schemas.indec import FoodVsWages, IndecOverview, LatestPoint

_IPC = "ipc_nacional"
_CANASTAS = "valorizacion_canastas_cba_cbt"
_SALARIOS = "indice_salarios"

# Clasificador esperado de cada serie del overview. Se fija para que, si un mismo
# código apareciera bajo dos clasificadores, no se elija uno al azar.
_CLS_IPC_GENERAL = "IPC"
_CLS_IPC_COICOP = "COICOP Argentina 2019"
_CLS_CANASTAS = "CBA y CBT"
_CLS_SALARIOS = "IS 2001"


def get_series(
    db: Session,
    *,
    dataset: str,
    code: str | None = None,
    region: str | None = None,
    indicator: str | None = None,
    classifier: str | None = None,
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
    if date_from is not None:
        query = query.filter(IndecObservation.period >= date_from)
    if date_to is not None:
        query = query.filter(IndecObservation.period <= date_to)
    return query.order_by(IndecObservation.period.asc()).limit(limit).all()


def build_food_vs_wages(
    ipc: dict[date, float], wages: dict[date, float], months: int = 24
) -> FoodVsWages | None:
    """
    Toma los últimos `months` períodos presentes en AMBAS series y reescala cada
    una a base 100 en el primer período común (redondeado a 2 decimales).
    None si hay menos de 2 comunes o si algún valor base es 0.
    """
    common = sorted(set(ipc) & set(wages))[-months:]
    if len(common) < 2:
        return None
    first = common[0]
    if ipc[first] == 0 or wages[first] == 0:
        return None  # no se puede reescalar a base 100 desde cero
    return FoodVsWages(
        labels=[p.strftime("%Y-%m") for p in common],
        ipc_alimentos=[round(ipc[p] / ipc[first] * 100, 2) for p in common],
        salarios=[round(wages[p] / wages[first] * 100, 2) for p in common],
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
    return IndecOverview(
        ipc_general_mensual=_latest_point(db, _IPC, _CLS_IPC_GENERAL, "0", "Nacional", "v_m"),
        ipc_general_interanual=_latest_point(db, _IPC, _CLS_IPC_GENERAL, "0", "Nacional", "v_ia"),
        ipc_alimentos_mensual=_latest_point(db, _IPC, _CLS_IPC_COICOP, "01", "Nacional", "v_m"),
        ipc_alimentos_interanual=_latest_point(db, _IPC, _CLS_IPC_COICOP, "01", "Nacional", "v_ia"),
        cba=_latest_point(db, _CANASTAS, _CLS_CANASTAS, "CBA", "GBA", "CBA"),
        cbt=_latest_point(db, _CANASTAS, _CLS_CANASTAS, "CBT", "GBA", "CBT"),
        ice=_latest_point(db, _CANASTAS, _CLS_CANASTAS, "ICE", "GBA", "ICE"),
        food_vs_wages=build_food_vs_wages(_as_dict(ipc_alimentos), _as_dict(salarios)),
    )
