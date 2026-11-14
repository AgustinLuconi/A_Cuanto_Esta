"""
Pruebas de los endpoints /api/v1/indec y de la lógica pura del overview.
La base se sustituye con un mock y las consultas se parchean; no hay red ni DB.
"""
import os
import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from app.config.database import get_db
from app.main import app
from app.schemas.indec import IndecOverview
from app.services.indec.queries import build_food_vs_wages

GET_SERIES = "app.services.indec.queries.get_series"
GET_OVERVIEW = "app.services.indec.queries.get_overview"


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


def test_series_requires_dataset(client):
    assert client.get("/api/v1/indec/series").status_code == 422


def test_series_passes_filters_to_query(client):
    url = (
        "/api/v1/indec/series?dataset=ipc_nacional&code=01&region=Nacional"
        "&indicator=Indice&classifier=COICOP%20Argentina%202019"
        "&from=2026-01-01&to=2026-10-01&limit=50"
    )
    with patch(GET_SERIES, return_value=[]) as mock_query:
        response = client.get(url)

    assert response.status_code == 200
    kwargs = mock_query.call_args.kwargs
    assert kwargs["dataset"] == "ipc_nacional"
    assert kwargs["code"] == "01"
    assert kwargs["region"] == "Nacional"
    assert kwargs["indicator"] == "Indice"
    assert kwargs["classifier"] == "COICOP Argentina 2019"
    assert kwargs["date_from"] == date(2026, 1, 1)
    assert kwargs["date_to"] == date(2026, 10, 1)
    assert kwargs["limit"] == 50


def test_series_rejects_limit_above_5000(client):
    response = client.get("/api/v1/indec/series?dataset=ipc_nacional&limit=5001")
    assert response.status_code == 422


def test_series_serializes_observations(client):
    obs = SimpleNamespace(
        dataset="ipc_nacional",
        classifier="COICOP Argentina 2019",
        level="División",
        series_code="01",
        series_name="Alimentos y bebidas no alcohólicas",
        region="Nacional",
        indicator_type="v_m",
        unit="Porcentaje",
        period=date(2026, 10, 1),
        value=Decimal("2.1000"),
    )
    with patch(GET_SERIES, return_value=[obs]):
        response = client.get("/api/v1/indec/series?dataset=ipc_nacional")

    assert response.status_code == 200
    assert response.json() == [
        {
            "dataset": "ipc_nacional",
            "classifier": "COICOP Argentina 2019",
            "level": "División",
            "series_code": "01",
            "series_name": "Alimentos y bebidas no alcohólicas",
            "region": "Nacional",
            "indicator_type": "v_m",
            "unit": "Porcentaje",
            "period": "2026-10-01",
            "value": 2.1,
        }
    ]


def test_overview_with_empty_table_returns_nulls_not_error(client):
    with patch(GET_OVERVIEW, return_value=IndecOverview()):
        response = client.get("/api/v1/indec/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["ipc_alimentos_interanual"] is None
    assert body["cba"] is None
    assert body["food_vs_wages"] is None


def test_build_food_vs_wages_rebases_to_100_on_first_common_period():
    ipc = {date(2026, 1, 1): 200.0, date(2026, 2, 1): 220.0, date(2026, 3, 1): 242.0}
    wages = {date(2026, 2, 1): 50.0, date(2026, 3, 1): 55.0, date(2026, 4, 1): 60.0}

    result = build_food_vs_wages(ipc, wages)

    assert result.labels == ["2026-02", "2026-03"]
    assert result.ipc_alimentos == [100.0, 110.0]
    assert result.salarios == [100.0, 110.0]


def test_build_food_vs_wages_limits_to_last_months():
    periods = [date(2024 + i // 12, i % 12 + 1, 1) for i in range(30)]
    ipc = {p: 100.0 + i for i, p in enumerate(periods)}
    wages = {p: 50.0 + i for i, p in enumerate(periods)}

    result = build_food_vs_wages(ipc, wages, months=24)

    assert len(result.labels) == 24
    assert result.labels[-1] == "2026-06"
    assert result.ipc_alimentos[0] == 100.0
    assert result.salarios[0] == 100.0


def test_build_food_vs_wages_returns_none_with_fewer_than_two_common_periods():
    ipc = {date(2026, 1, 1): 1.0, date(2026, 2, 1): 2.0}
    wages = {date(2026, 2, 1): 5.0, date(2026, 3, 1): 6.0}

    assert build_food_vs_wages(ipc, wages) is None
