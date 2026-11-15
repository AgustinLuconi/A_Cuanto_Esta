"""
Cargador de observaciones del INDEC: convierte filas crudas de la API en
observaciones normalizadas y las persiste con upsert idempotente.

El upsert (INSERT ... ON CONFLICT DO UPDATE) es necesario porque el INDEC
revisa valores ya publicados: una segunda corrida actualiza en vez de duplicar.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import literal_column, or_
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
    "indicator",
    "indicator_type",
    "period",
)


@dataclass
class UpsertResult:
    inserted: int
    updated: int
    unchanged: int = 0  # ya estaban guardadas con el mismo contenido


def _parse_period(raw) -> date | None:
    """'202610' -> date(2026, 10, 1). None si el formato no es YYYYMM válido."""
    try:
        text = str(raw)
        if len(text) != 6:
            return None
        return date(int(text[:4]), int(text[4:]), 1)
    except (TypeError, ValueError):
        return None


def _to_observation(spec: DatasetSpec, row: dict) -> dict | None:
    """Una fila cruda -> observación, o None si no es utilizable."""
    period = _parse_period(row.get("periodo"))
    if period is None or row.get("valor") is None:
        return None
    try:
        value = Decimal(str(row["valor"]))
        if not value.is_finite():  # NaN / Infinity romperían el JSON de la API
            return None
        return {
            "dataset": spec.slug,
            "classifier": row["clasificador"],
            "level": row["nivel"],
            "series_code": row[spec.code_column],
            "series_name": row["descripcion"],
            "region": (row.get("region") or DEFAULT_REGION) if spec.has_region else DEFAULT_REGION,
            "indicator": (row.get(spec.indicator_column) or "") if spec.indicator_column else "",
            "indicator_type": row["tipo_de_indicador"],
            "unit": row.get("unidad_de_medida"),
            "indicator_description": row.get("tipo_de_indicador_descripcion"),
            "period": period,
            "value": value,
            "notes": row.get("observaciones"),
        }
    except (InvalidOperation, ValueError, KeyError, TypeError):
        # "s/d", "1,5", columna faltante...: se descarta la fila, no el lote
        return None


def normalize_rows(spec: DatasetSpec, rows: list[dict], *, report: bool = True) -> list[dict]:
    """
    Filas crudas del INDEC -> dicts con las columnas de IndecObservation.
    Descarta filas no utilizables (sin valor, valor no numérico o no finito,
    período inválido, columnas faltantes) y deduplica por la clave única
    conservando la última aparición. Con `report=True` informa cuántas filas se
    descartaron y cuántas eran duplicadas: la clave única no incluye todas las
    columnas del INDEC, así que un duplicado con valor distinto es una señal.
    """
    if spec.reshape is not None:
        rows = spec.reshape(rows)  # datasets en formato no estándar (ej. canasta-crianza)
    by_key: dict[tuple, dict] = {}
    dropped = duplicates = conflicting = 0
    for row in rows:
        observation = _to_observation(spec, row)
        if observation is None:
            dropped += 1
            continue
        key = tuple(observation[f] for f in _KEY_FIELDS)
        previous = by_key.get(key)
        if previous is not None:
            duplicates += 1
            if previous["value"] != observation["value"]:
                conflicting += 1
        by_key[key] = observation
    if report and (dropped or duplicates):
        print(
            f"[indec] {spec.slug}: {dropped} descartadas, {duplicates} duplicadas "
            f"({conflicting} con valores distintos) de {len(rows)} filas"
        )
    return list(by_key.values())


def upsert_observations(
    session: Session, rows: list[dict], batch_size: int = 1000
) -> UpsertResult:
    """
    Inserta o actualiza observaciones ya normalizadas, en lotes. No hace commit:
    el llamador decide cuándo persistir (un commit por dataset).
    """
    inserted = updated = unchanged = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        stmt = insert(IndecObservation).values(batch)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_indec_observation_key",
            set_={
                "value": stmt.excluded.value,
                "series_name": stmt.excluded.series_name,
                "unit": stmt.excluded.unit,
                "indicator_description": stmt.excluded.indicator_description,
                "notes": stmt.excluded.notes,
                "ingested_at": utcnow_aware(),
            },
            # Solo se reescribe lo que realmente cambió: así `ingested_at` es
            # "cuándo se cargó o se modificó" y no "última vez que se vio", y
            # `updated` cuenta revisiones reales del INDEC.
            where=or_(
                IndecObservation.value.is_distinct_from(stmt.excluded.value),
                IndecObservation.series_name.is_distinct_from(stmt.excluded.series_name),
                IndecObservation.unit.is_distinct_from(stmt.excluded.unit),
                IndecObservation.indicator_description.is_distinct_from(
                    stmt.excluded.indicator_description
                ),
                IndecObservation.notes.is_distinct_from(stmt.excluded.notes),
            ),
        ).returning(literal_column("(xmax = 0)"))
        # xmax = 0 solo en filas recién insertadas; en las actualizadas es > 0.
        # Las filas sin cambios no se devuelven (el WHERE del upsert las omite).
        flags = session.execute(stmt).all()
        for (was_inserted,) in flags:
            if was_inserted:
                inserted += 1
            else:
                updated += 1
        unchanged += len(batch) - len(flags)
    return UpsertResult(inserted=inserted, updated=updated, unchanged=unchanged)
