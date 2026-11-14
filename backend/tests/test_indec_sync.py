"""
Pruebas del orquestador de sincronización del INDEC y del script CLI.
Cliente y sesión son mocks; no hay red ni base de datos.
"""
import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.services.indec.client import IndecError
from app.services.indec.loader import UpsertResult
from app.services.indec.registry import DatasetSpec
from app.services.indec.sync import (
    EmptyDatasetError,
    SyncReport,
    SyncResult,
    sync_all,
    sync_dataset,
)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import fetch_indec_data  # noqa: E402

LATEST = "app.services.indec.sync.latest_period"
UPSERT = "app.services.indec.sync.upsert_observations"

SPEC = DatasetSpec(
    slug="ipc_nacional",
    slices=({"codigo": "eq.0"}, {"nivel": "eq.Producto"}),
    has_region=True,
    order="periodo.asc",
)


def _raw(periodo="202610", valor=1.0, codigo="0"):
    return {
        "clasificador": "IPC",
        "nivel": "Nivel General",
        "codigo": codigo,
        "descripcion": "Nivel general",
        "periodo": periodo,
        "tipo_de_indicador": "v_m",
        "region": "Nacional",
        "unidad_de_medida": "Porcentaje",
        "valor": valor,
        "observaciones": None,
    }


def _client(rows_per_call=None):
    client = MagicMock()
    client.fetch.return_value = rows_per_call if rows_per_call is not None else [_raw()]
    return client


def _fetch_params(client):
    return [c.args[1] for c in client.fetch.call_args_list]


def test_incremental_adds_periodo_gte_with_three_month_window():
    client = _client()
    with patch(LATEST, return_value=date(2026, 10, 1)), patch(UPSERT, return_value=UpsertResult(1, 0)):
        sync_dataset(MagicMock(), client, SPEC)

    assert all(p["periodo"] == "gte.202607" for p in _fetch_params(client))


def test_full_flag_skips_periodo_filter():
    client = _client()
    with patch(LATEST, return_value=date(2026, 10, 1)), patch(UPSERT, return_value=UpsertResult(1, 0)):
        sync_dataset(MagicMock(), client, SPEC, full=True)

    assert all("periodo" not in p for p in _fetch_params(client))


def test_no_stored_data_fetches_everything():
    client = _client()
    with patch(LATEST, return_value=None), patch(UPSERT, return_value=UpsertResult(1, 0)):
        sync_dataset(MagicMock(), client, SPEC)

    assert all("periodo" not in p for p in _fetch_params(client))


def test_fetches_each_slice_and_merges_rows():
    client = MagicMock()
    client.fetch.side_effect = [[_raw(codigo="0")], [_raw(codigo="1"), _raw(codigo="2")]]
    with patch(LATEST, return_value=None), patch(UPSERT, return_value=UpsertResult(3, 0)):
        result = sync_dataset(MagicMock(), client, SPEC)

    assert client.fetch.call_count == 2
    assert [p.get("codigo") or p.get("nivel") for p in _fetch_params(client)] == ["eq.0", "eq.Producto"]
    assert result.fetched == 3


def test_empty_fetch_raises_empty_dataset_error_before_writing():
    session = MagicMock()
    with patch(LATEST, return_value=None), patch(UPSERT) as mock_upsert:
        with pytest.raises(EmptyDatasetError):
            sync_dataset(session, _client(rows_per_call=[]), SPEC)

    mock_upsert.assert_not_called()
    session.commit.assert_not_called()


def test_all_rows_null_value_raises_empty_dataset_error():
    rows = [_raw(valor=None), _raw(periodo="202609", valor=None)]
    with patch(LATEST, return_value=None), patch(UPSERT) as mock_upsert:
        with pytest.raises(EmptyDatasetError):
            sync_dataset(MagicMock(), _client(rows_per_call=rows), SPEC)

    mock_upsert.assert_not_called()


def test_commits_once_per_dataset():
    session = MagicMock()
    with patch(LATEST, return_value=None), patch(UPSERT, return_value=UpsertResult(2, 1)):
        result = sync_dataset(session, _client(), SPEC)

    session.commit.assert_called_once()
    assert result == SyncResult(dataset="ipc_nacional", fetched=2, inserted=2, updated=1)


def test_sync_all_continues_after_error_and_reports_it():
    session = MagicMock()
    other = DatasetSpec(slug="indice_salarios", slices=({},), has_region=False, order="periodo.asc")
    client = MagicMock()
    client.fetch.side_effect = [IndecError("boom"), [_raw()]]
    with patch(LATEST, return_value=None), patch(UPSERT, return_value=UpsertResult(1, 0)):
        report = sync_all(session, client, [SPEC, other])

    assert report.errors == {"ipc_nacional": "boom"}
    assert [r.dataset for r in report.results] == ["indice_salarios"]
    session.rollback.assert_called()


def test_main_returns_1_when_token_missing(monkeypatch):
    monkeypatch.setattr("app.services.indec.client.settings.INDEC_API_TOKEN", None)

    assert fetch_indec_data.main([]) == 1


def test_main_unknown_dataset_returns_1():
    assert fetch_indec_data.main(["--dataset", "nope"]) == 1


def test_main_returns_1_when_report_has_errors():
    report = SyncReport(results=[], errors={"ipc_nacional": "boom"})
    with patch.object(fetch_indec_data, "IndecClient"), \
         patch.object(fetch_indec_data, "SessionLocal"), \
         patch.object(fetch_indec_data, "sync_all", return_value=report):
        assert fetch_indec_data.main([]) == 1


def test_main_returns_0_on_success_and_passes_full_flag():
    report = SyncReport(results=[SyncResult("ipc_nacional", 10, 3, 7)], errors={})
    with patch.object(fetch_indec_data, "IndecClient"), \
         patch.object(fetch_indec_data, "SessionLocal"), \
         patch.object(fetch_indec_data, "sync_all", return_value=report) as mock_sync:
        assert fetch_indec_data.main(["--full"]) == 0

    assert mock_sync.call_args.kwargs["full"] is True
