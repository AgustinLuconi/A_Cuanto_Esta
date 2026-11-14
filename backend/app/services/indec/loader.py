"""
Cargador de observaciones del INDEC: convierte filas crudas de la API en
observaciones normalizadas y las persiste con upsert idempotente.

El upsert (INSERT ... ON CONFLICT DO UPDATE) es necesario porque el INDEC
revisa valores ya publicados: una segunda corrida actualiza en vez de duplicar.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import literal_column
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.indec_observation import IndecObservation
from app.services.indec.registry import DatasetSpec
from app.utils.time import utcnow_aware

# Región que se asigna a los datasets que no la traen (ej. indice_salarios)
DEFAULT_REGION = "Nacional"

_KEY_FIELDS = (
    "dataset",
    "classifier",
    "level",
    "series_code",
    "region",
    "indicator_type",
    "period",
)


@dataclass
class UpsertResult:
    inserted: int
    updated: int


def _parse_period(raw) -> date | None:
    """'202610' -> date(2026, 10, 1). None si el formato no es YYYYMM válido."""
    try:
        text = str(raw)
        if len(text) != 6:
            return None
        return date(int(text[:4]), int(text[4:]), 1)
    except (TypeError, ValueError):
        return None


def normalize_rows(spec: DatasetSpec, rows: list[dict]) -> list[dict]:
    """
    Filas crudas del INDEC -> dicts con las columnas de IndecObservation.
    Descarta filas sin `valor` o con `periodo` inválido, y deduplica por la
    clave única conservando la última aparición.
    """
    by_key: dict[tuple, dict] = {}
    for row in rows:
        period = _parse_period(row.get("periodo"))
        if period is None or row.get("valor") is None:
            continue
        observation = {
            "dataset": spec.slug,
            "classifier": row["clasificador"],
            "level": row["nivel"],
            "series_code": row["codigo"],
            "series_name": row["descripcion"],
            "region": (row.get("region") or DEFAULT_REGION) if spec.has_region else DEFAULT_REGION,
            "indicator_type": row["tipo_de_indicador"],
            "unit": row.get("unidad_de_medida"),
            "period": period,
            "value": Decimal(str(row["valor"])),
            "notes": row.get("observaciones"),
        }
        by_key[tuple(observation[f] for f in _KEY_FIELDS)] = observation
    return list(by_key.values())


def upsert_observations(
    session: Session, rows: list[dict], batch_size: int = 1000
) -> UpsertResult:
    """
    Inserta o actualiza observaciones ya normalizadas, en lotes. No hace commit:
    el llamador decide cuándo persistir (un commit por dataset).
    """
    inserted = updated = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        stmt = insert(IndecObservation).values(batch)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_indec_observation_key",
            set_={
                "value": stmt.excluded.value,
                "series_name": stmt.excluded.series_name,
                "unit": stmt.excluded.unit,
                "notes": stmt.excluded.notes,
                "ingested_at": utcnow_aware(),
            },
        ).returning(literal_column("(xmax = 0)"))
        # xmax = 0 solo en filas recién insertadas; en las actualizadas es > 0
        for (was_inserted,) in session.execute(stmt).all():
            if was_inserted:
                inserted += 1
            else:
                updated += 1
    return UpsertResult(inserted=inserted, updated=updated)
