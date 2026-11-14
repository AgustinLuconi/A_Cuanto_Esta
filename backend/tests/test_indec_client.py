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
    with patch(HTTPX_GET, return_value=_resp(_rows(1))) as mock_get:
        _client().fetch("ipc_nacional", {"codigo": "in.(0,01)"}, ORDER)

    assert mock_get.call_args[0][0].endswith("/v1/ipc_nacional")
    kwargs = mock_get.call_args[1]
    assert kwargs["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert kwargs["params"] == {
        "codigo": "in.(0,01)",
        "order": ORDER,
        "limit": 1000,
        "offset": 0,
    }


def test_fetch_paginates_until_short_page():
    pages = [_resp(_rows(1000)), _resp(_rows(3, start=1000))]
    with patch(HTTPX_GET, side_effect=pages) as mock_get:
        rows = _client().fetch("ipc_nacional", {}, ORDER)

    assert len(rows) == 1003
    offsets = [c[1]["params"]["offset"] for c in mock_get.call_args_list]
    assert offsets == [0, 1000]


def test_fetch_requests_next_page_after_exactly_full_page():
    # Una página de exactamente 1000 filas no implica que no haya más datos
    pages = [_resp(_rows(1000)), _resp([])]
    with patch(HTTPX_GET, side_effect=pages) as mock_get:
        rows = _client().fetch("ipc_nacional", {}, ORDER)

    assert len(rows) == 1000
    assert mock_get.call_count == 2


def test_fetch_retries_on_5xx_then_succeeds():
    responses = [_resp(None, 503), _resp(None, 503), _resp(_rows(2))]
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
    assert "vence" in out
    assert "5" in out
    assert token not in out
