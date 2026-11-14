"""
Pruebas de las consultas de lectura sobre indec_observations, contra una base
SQLite en memoria (la tabla se crea desde el modelo). Ejecutan SQL real, a
diferencia de los tests de API, que parchean las consultas.
"""
import os
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.indec_observation import IndecObservation
from app.services.indec.queries import get_overview, get_series
from app.services.indec.sync import latest_period


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    IndecObservation.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _add(db, *, dataset="ipc_nacional", classifier="IPC", level="Nivel General",
         code="0", region="Nacional", indicator="v_m", period=date(2026, 10, 1), value=1.0):
    db.add(IndecObservation(
        dataset=dataset, classifier=classifier, level=level, series_code=code,
        series_name="x", region=region, indicator_type=indicator, unit=None,
        period=period, value=Decimal(str(value)),
    ))
    db.commit()


def test_get_series_filters_orders_and_limits(db):
    _add(db, code="01", classifier="COICOP Argentina 2019", period=date(2026, 3, 1), value=3)
    _add(db, code="01", classifier="COICOP Argentina 2019", period=date(2026, 1, 1), value=1)
    _add(db, code="01", classifier="COICOP Argentina 2019", period=date(2026, 2, 1), value=2)
    _add(db, code="0", period=date(2026, 2, 1), value=99)  # otra serie

    rows = get_series(db, dataset="ipc_nacional", code="01", date_from=date(2026, 2, 1))
    assert [r.period for r in rows] == [date(2026, 2, 1), date(2026, 3, 1)]

    assert len(get_series(db, dataset="ipc_nacional", code="01", limit=2)) == 2
    assert get_series(db, dataset="ipc_nacional", classifier="IPC")[0].series_code == "0"


def test_get_series_returns_empty_list_for_unknown_dataset(db):
    assert get_series(db, dataset="no_existe") == []


def test_latest_period_returns_max_or_none(db):
    assert latest_period(db, "ipc_nacional") is None
    _add(db, period=date(2026, 8, 1))
    _add(db, period=date(2026, 10, 1))
    assert latest_period(db, "ipc_nacional") == date(2026, 10, 1)
    assert latest_period(db, "indice_salarios") is None


def test_overview_on_empty_table_is_all_none(db):
    overview = get_overview(db)

    assert overview.ipc_general_mensual is None
    assert overview.cba is None
    assert overview.food_vs_wages is None


def test_overview_picks_latest_period_per_series(db):
    _add(db, period=date(2026, 9, 1), value=2.0)
    _add(db, period=date(2026, 10, 1), value=2.4)

    overview = get_overview(db)

    assert overview.ipc_general_mensual.period == date(2026, 10, 1)
    assert overview.ipc_general_mensual.value == 2.4


def test_overview_ignores_same_code_under_another_classifier(db):
    # Si un mismo código aparece bajo dos clasificadores, el overview debe usar
    # el esperado y no elegir uno al azar.
    _add(db, classifier="COICOP Argentina 2019", level="División", code="01", value=4.4)
    _add(db, classifier="Bienes y servicios", level="Categoría", code="01", value=9.9)

    assert get_overview(db).ipc_alimentos_mensual.value == 4.4


def test_overview_builds_canastas_and_food_vs_wages(db):
    for code in ("CBA", "CBT", "ICE"):
        _add(db, dataset="valorizacion_canastas_cba_cbt", classifier="CBA y CBT",
             level="Adulto equivalente", code=code, region="GBA", indicator=code, value=100)
    for month, (ipc, wage) in enumerate([(200, 50), (220, 55)], start=1):
        period = date(2026, month, 1)
        _add(db, classifier="COICOP Argentina 2019", level="División", code="01",
             indicator="Indice", period=period, value=ipc)
        _add(db, dataset="indice_salarios", classifier="IS 2001", level="0", code="0",
             indicator="Indice", period=period, value=wage)

    overview = get_overview(db)

    assert overview.cba.value == overview.cbt.value == overview.ice.value == 100
    assert overview.food_vs_wages.ipc_alimentos == [100.0, 110.0]
    assert overview.food_vs_wages.salarios == [100.0, 110.0]
