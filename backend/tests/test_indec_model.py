"""
Pruebas del modelo IndecObservation. Inspeccionan la definición de la tabla
(metadata de SQLAlchemy); no tocan la base de datos.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import UniqueConstraint

from app.models.indec_observation import IndecObservation

TABLE = IndecObservation.__table__


def test_region_is_not_nullable():
    # NULL rompería la unicidad: en PostgreSQL dos NULL no cuentan como iguales
    assert not TABLE.c.region.nullable


def test_unit_and_notes_are_nullable():
    assert TABLE.c.unit.nullable
    assert TABLE.c.notes.nullable


def test_unique_constraint_covers_full_key():
    constraints = {
        c.name: {col.name for col in c.columns}
        for c in TABLE.constraints
        if isinstance(c, UniqueConstraint)
    }
    assert constraints["uq_indec_observation_key"] == {
        "dataset",
        "classifier",
        "level",
        "series_code",
        "region",
        "indicator_type",
        "period",
    }


def test_ingested_at_is_timezone_aware():
    assert TABLE.c.ingested_at.type.timezone is True
