"""
Orquestador de la sincronización con el INDEC.

Por cada dataset del registro: pide los cortes (slices) al cliente, normaliza,
y hace upsert. Un commit por dataset: si uno falla, los anteriores ya quedaron
guardados.

Modo incremental (por defecto): pide desde (último período guardado − 3 meses)
para capturar revisiones del INDEC. Esa ventana siempre contiene datos, así que
traer 0 filas significa que algo falló y se lanza EmptyDatasetError.
"""
from dataclasses import dataclass, field
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.indec_observation import IndecObservation
from app.services.indec.client import IndecClient, IndecError
from app.services.indec.loader import normalize_rows, upsert_observations
from app.services.indec.registry import DatasetSpec

# Meses hacia atrás desde el último período guardado que se vuelven a pedir
REVISION_WINDOW_MONTHS = 3


class EmptyDatasetError(IndecError):
    """El INDEC no devolvió filas utilizables para un dataset."""


@dataclass
class SyncResult:
    dataset: str
    fetched: int
    inserted: int
    updated: int


@dataclass
class SyncReport:
    results: list[SyncResult] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


def latest_period(session: Session, dataset: str) -> date | None:
    """Último período guardado del dataset, o None si todavía no hay datos."""
    return (
        session.query(func.max(IndecObservation.period))
        .filter(IndecObservation.dataset == dataset)
        .scalar()
    )


def sync_dataset(
    session: Session, client: IndecClient, spec: DatasetSpec, *, full: bool = False
) -> SyncResult:
    """Sincroniza un dataset. Lanza EmptyDatasetError si no hay filas utilizables."""
    since = None if full else latest_period(session, spec.slug)
    period_filter = {}
    if since is not None:
        start = since - relativedelta(months=REVISION_WINDOW_MONTHS)
        period_filter = {"periodo": f"gte.{start:%Y%m}"}

    raw_rows: list[dict] = []
    for slice_ in spec.slices:
        slice_rows = client.fetch(spec.slug, {**slice_, **period_filter}, spec.order)
        # Cada corte debe traer filas utilizables por sí mismo: uno vacío no
        # puede quedar tapado por otro con datos (el job saldría "en verde"
        # con una serie desactualizada).
        if not normalize_rows(spec, slice_rows, report=False):
            raise EmptyDatasetError(
                f"{spec.slug}: el corte {slice_} no devolvió filas utilizables "
                f"({len(slice_rows)} crudas)"
            )
        raw_rows.extend(slice_rows)

    observations = normalize_rows(spec, raw_rows)
    result = upsert_observations(session, observations)
    session.commit()
    return SyncResult(
        dataset=spec.slug,
        fetched=len(raw_rows),
        inserted=result.inserted,
        updated=result.updated,
    )


def sync_all(
    session: Session, client: IndecClient, specs: list[DatasetSpec], *, full: bool = False
) -> SyncReport:
    """Sincroniza todos los datasets; cualquier error en uno no frena a los demás."""
    report = SyncReport()
    for spec in specs:
        try:
            report.results.append(sync_dataset(session, client, spec, full=full))
        except Exception as e:  # noqa: BLE001 — un dataset roto no debe frenar a los demás
            session.rollback()
            report.errors[spec.slug] = (
                str(e) if isinstance(e, IndecError) else f"{type(e).__name__}: {e}"
            )
    return report
