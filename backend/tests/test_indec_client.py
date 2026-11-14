"""
Pruebas de IndecClient: autenticación Bearer, paginación, reintentos y errores.
Se parchea httpx.get y time.sleep; no hay red real.
"""
import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.indec.client import (
    IndecAuthError,
    IndecClient,
    IndecError,
    token_days_remaining,
)

HTTPX_GET = "app.services.indec.client.httpx.get"
SLEEP = "app.services.indec.client.time.sleep"
TOKEN = "tok-secreto-123"
ORDER = "periodo.asc,codigo.asc"


def _resp(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    return resp


def _rows(n, start=0):
    return [{"periodo": "202601", "codigo": str(start + i), "valor": 1.0} for i in range(n)]


def _client(**kwargs):
    return IndecClient(token=TOKEN, retry_backoff=0, **kwargs)


def _make_jwt(exp: datetime) -> str:
    def b64(data: dict) -> str:
        raw = json.dumps(data).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{b64({'alg': 'HS256'})}.{b64({'exp': int(exp.timestamp())})}.firma"


def test_fetch_sends_bearer_header_and_url():
    with patch(HTTPX_GET, side_effect=[_resp(_rows(1)), _resp([])]) as mock_get:
        _client().fetch("ipc_nacional", {"codigo": "in.(0,01)"}, ORDER)

    first_call = mock_get.call_args_list[0]
    assert first_call[0][0].endswith("/v1/ipc_nacional")
    kwargs = first_call[1]
    assert kwargs["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert kwargs["params"] == {
        "codigo": "in.(0,01)",
        "order": ORDER,
        "limit": 1000,
        "offset": 0,
    }


def test_fetch_paginates_until_empty_page():
    pages = [_resp(_rows(1000)), _resp(_rows(3, start=1000)), _resp([])]
    with patch(HTTPX_GET, side_effect=pages) as mock_get:
        rows = _client().fetch("ipc_nacional", {}, ORDER)

    assert len(rows) == 1003
    offsets = [c[1]["params"]["offset"] for c in mock_get.call_args_list]
    assert offsets == [0, 1000, 1003]


def test_fetch_requests_next_page_after_exactly_full_page():
    # Una página de exactamente 1000 filas no implica que no haya más datos
    pages = [_resp(_rows(1000)), _resp([])]
    with patch(HTTPX_GET, side_effect=pages) as mock_get:
        rows = _client().fetch("ipc_nacional", {}, ORDER)

    assert len(rows) == 1000
    assert mock_get.call_count == 2


def test_fetch_retries_on_5xx_then_succeeds():
    responses = [_resp(None, 503), _resp(None, 503), _resp(_rows(2)), _resp([])]
    with patch(HTTPX_GET, side_effect=responses), patch(SLEEP) as mock_sleep:
        rows = _client().fetch("ipc_nacional", {}, ORDER)

    assert len(rows) == 2
    assert mock_sleep.call_count == 2


def test_fetch_raises_indec_error_after_exhausting_retries():
    with patch(HTTPX_GET, side_effect=httpx.ConnectError("boom")) as mock_get, patch(SLEEP):
        with pytest.raises(IndecError) as exc_info:
            _client().fetch("ipc_nacional", {}, ORDER)

    assert not isinstance(exc_info.value, IndecAuthError)
    assert mock_get.call_count == 3


def test_fetch_raises_auth_error_on_401_without_retry():
    with patch(HTTPX_GET, return_value=_resp(None, 401)) as mock_get, patch(SLEEP) as mock_sleep:
        with pytest.raises(IndecAuthError) as exc_info:
            _client().fetch("ipc_nacional", {}, ORDER)

    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()
    assert TOKEN not in str(exc_info.value)


def test_fetch_raises_on_non_list_payload():
    with patch(HTTPX_GET, return_value=_resp({"message": "algo raro"})):
        with pytest.raises(IndecError):
            _client().fetch("ipc_nacional", {}, ORDER)


def test_init_without_token_raises_auth_error(monkeypatch):
    monkeypatch.setattr("app.services.indec.client.settings.INDEC_API_TOKEN", None)
    with pytest.raises(IndecAuthError):
        IndecClient(token=None)


def test_token_days_remaining():
    now = datetime(2026, 11, 14, tzinfo=timezone.utc)
    token = _make_jwt(now + timedelta(days=10))

    assert token_days_remaining(token, now=now) == 10
    assert token_days_remaining("esto-no-es-un-jwt", now=now) is None


def test_init_warns_when_token_expires_soon(capsys):
    token = _make_jwt(datetime.now(timezone.utc) + timedelta(days=5, hours=1))
    IndecClient(token=token)

    out = capsys.readouterr().out
    assert "vence en 5 días" in out
    assert token not in out


def test_fetch_raises_indec_error_on_non_json_body():
    broken = _resp(None)
    broken.json.side_effect = ValueError("no es JSON")
    with patch(HTTPX_GET, return_value=broken):
        with pytest.raises(IndecError):
            _client().fetch("ipc_nacional", {}, ORDER)


def test_fetch_advances_offset_by_actual_page_length():
    # Si el INDEC baja su tope por request (ej. a 500), una página corta no
    # significa "fin" y el offset debe avanzar por lo recibido, no por page_size.
    pages = [_resp(_rows(500)), _resp(_rows(500, start=500)), _resp([])]
    with patch(HTTPX_GET, side_effect=pages) as mock_get:
        rows = _client().fetch("ipc_nacional", {}, ORDER)

    assert len(rows) == 1000
    offsets = [c[1]["params"]["offset"] for c in mock_get.call_args_list]
    assert offsets == [0, 500, 1000]


def test_fetch_raises_if_server_ignores_offset():
    # Un servidor que ignora `offset` devolvería siempre las mismas filas: sin
    # tope de páginas el job giraría hasta agotar el timeout de 15 minutos.
    with patch(HTTPX_GET, return_value=_resp(_rows(5))) as mock_get:
        with pytest.raises(IndecError):
            _client(max_pages=3).fetch("ipc_nacional", {}, ORDER)

    assert mock_get.call_count == 3


def test_fetch_retries_on_429_then_succeeds():
    responses = [_resp(None, 429), _resp(_rows(1)), _resp([])]
    with patch(HTTPX_GET, side_effect=responses), patch(SLEEP) as mock_sleep:
        rows = _client().fetch("ipc_nacional", {}, ORDER)

    assert len(rows) == 1
    assert mock_sleep.call_count == 1


def test_fetch_raises_auth_error_on_403_without_retry():
    with patch(HTTPX_GET, return_value=_resp(None, 403)) as mock_get, patch(SLEEP) as mock_sleep:
        with pytest.raises(IndecAuthError) as exc_info:
            _client().fetch("ipc_nacional", {}, ORDER)

    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()
    assert TOKEN not in str(exc_info.value)


def test_init_reports_already_expired_token(capsys):
    token = _make_jwt(datetime.now(timezone.utc) - timedelta(days=3))
    IndecClient(token=token)

    out = capsys.readouterr().out
    assert "VENCIÓ" in out
    assert "-" not in out  # nada de "vence en -4 días"
    assert token not in out
