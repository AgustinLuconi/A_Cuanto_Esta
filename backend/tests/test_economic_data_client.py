"""Tests para los métodos nuevos de ArgentinaDatosClient: riesgo país y todos los dólares."""
import httpx
from unittest.mock import MagicMock, patch

from app.services.economic_data.client import ArgentinaDatosClient


def _fake_response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_get_risk_country_parses_response():
    payload = [
        {"fecha": "2026-07-24", "valor": 437},
        {"fecha": "2026-07-23", "valor": 437},
    ]
    with patch(
        "app.services.economic_data.client.httpx.get",
        return_value=_fake_response(payload),
    ) as mock_get:
        client = ArgentinaDatosClient()
        records = client.get_risk_country()

    called_url = mock_get.call_args[0][0]
    assert called_url.endswith("/v1/finanzas/indices/riesgo-pais")
    assert len(records) == 2
    assert records[0].valor == 437
    assert records[0].fecha.isoformat() == "2026-07-24"


def test_get_risk_country_returns_empty_list_on_error():
    with patch(
        "app.services.economic_data.client.httpx.get",
        side_effect=httpx.ConnectError("boom"),
    ):
        client = ArgentinaDatosClient()
        records = client.get_risk_country()

    assert records == []


def test_get_all_dollars_parses_multiple_casas():
    payload = [
        {"casa": "blue", "compra": 1300.0, "venta": 1320.0, "fecha": "2026-07-24"},
        {"casa": "mayorista", "compra": 1000.0, "venta": 1005.0, "fecha": "2026-07-24"},
    ]
    with patch(
        "app.services.economic_data.client.httpx.get",
        return_value=_fake_response(payload),
    ) as mock_get:
        client = ArgentinaDatosClient()
        records = client.get_all_dollars()

    called_url = mock_get.call_args[0][0]
    assert called_url.endswith("/v1/cotizaciones/dolares")
    assert len(records) == 2
    assert {r.casa for r in records} == {"blue", "mayorista"}
    assert [r.venta for r in records if r.casa == "blue"][0] == 1320.0


def test_get_estado_parses_response():
    with patch(
        "app.services.economic_data.client.httpx.get",
        return_value=_fake_response({"estado": "Correcto"}),
    ) as mock_get:
        client = ArgentinaDatosClient()
        estado = client.get_estado()

    called_url = mock_get.call_args[0][0]
    assert called_url.endswith("/v1/estado")
    assert estado == "Correcto"


def test_get_estado_returns_none_on_error():
    with patch(
        "app.services.economic_data.client.httpx.get",
        side_effect=httpx.ConnectError("boom"),
    ):
        client = ArgentinaDatosClient()
        estado = client.get_estado()

    assert estado is None


def test_get_retries_on_transient_502_error_and_succeeds():
    mock_502 = MagicMock()
    mock_502.status_code = 502
    err_502 = httpx.HTTPStatusError("502 Bad Gateway", request=MagicMock(), response=mock_502)
    resp_success = _fake_response({"estado": "Correcto"})

    with patch(
        "app.services.economic_data.client.httpx.get",
        side_effect=[err_502, resp_success],
    ) as mock_get:
        client = ArgentinaDatosClient(max_retries=3, retry_backoff=0.01)
        estado = client.get_estado()

    assert estado == "Correcto"
    assert mock_get.call_count == 2


def test_get_retries_up_to_max_attempts_and_returns_none():
    mock_502 = MagicMock()
    mock_502.status_code = 502
    err_502 = httpx.HTTPStatusError("502 Bad Gateway", request=MagicMock(), response=mock_502)

    with patch(
        "app.services.economic_data.client.httpx.get",
        side_effect=err_502,
    ) as mock_get:
        client = ArgentinaDatosClient(max_retries=3, retry_backoff=0.01)
        estado = client.get_estado()

    assert estado is None
    assert mock_get.call_count == 3

