"""
Pruebas del cargador de observaciones del INDEC: normalización de filas crudas
y upsert idempotente. La sesión de SQLAlchemy se mockea; no se toca la base.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from sqlalchemy.dialects import postgresql

from app.services.indec.loader import UpsertResult, normalize_rows, upsert_observations
from app.services.indec.registry import REGISTRY, DatasetSpec

IPC = REGISTRY["ipc_nacional"]
SALARIOS = REGISTRY["indice_salarios"]


def _ipc_row(**overrides):
    row = {
        "clasificador": "COICOP Argentina 2019",
        "nivel": "División",
        "codigo": "01",
        "descripcion": "Alimentos y bebidas no alcohólicas",
        "periodo": "202610",
        "tipo_de_indicador": "v_m",
        "region": "Nacional",
        "unidad_de_medida": "Porcentaje",
        "valor": 2.1,
        "observaciones": None,
    }
    row.update(overrides)
    return row


def _obs(i):
    """Observación ya normalizada, con clave distinta por `i`."""
    return {
        "dataset": "ipc_nacional",
        "classifier": "IPC",
        "level": "Nivel General",
        "series_code": str(i),
        "series_name": "x",
        "region": "Nacional",
        "indicator_type": "v_m",
        "unit": "Porcentaje",
        "indicator": "",
        "indicator_description": None,
        "period": date(2026, 10, 1),
        "value": Decimal("1.0"),
        "notes": None,
    }


def test_normalize_maps_fields_and_parses_period():
    [obs] = normalize_rows(IPC, [_ipc_row()])

    assert obs["dataset"] == "ipc_nacional"
    assert obs["classifier"] == "COICOP Argentina 2019"
    assert obs["level"] == "División"
    assert obs["series_code"] == "01"
    assert obs["series_name"] == "Alimentos y bebidas no alcohólicas"
    assert obs["indicator_type"] == "v_m"
    assert obs["unit"] == "Porcentaje"
    assert obs["region"] == "Nacional"
    assert obs["period"] == date(2026, 10, 1)
    assert obs["value"] == Decimal("2.1")


def test_normalize_forces_region_nacional_when_dataset_has_no_region():
    row = _ipc_row(clasificador="IS 2001", nivel="0", codigo="0", tipo_de_indicador="Indice")
    del row["region"]

    [obs] = normalize_rows(SALARIOS, [row])

    assert obs["region"] == "Nacional"


def test_normalize_drops_null_value_rows():
    rows = [_ipc_row(valor=None), _ipc_row(periodo="202609", valor=1.9)]

    result = normalize_rows(IPC, rows)

    assert [o["period"] for o in result] == [date(2026, 9, 1)]


def test_normalize_drops_invalid_period_rows():
    rows = [_ipc_row(periodo=p) for p in ("2026", "abcdef", None, "202613")]

    assert normalize_rows(IPC, rows) == []


def test_normalize_dedups_same_key_keeping_last():
    # PostgreSQL falla con "cannot affect row a second time" si el mismo lote
    # trae dos filas con la misma clave única.
    rows = [_ipc_row(valor=1.0), _ipc_row(valor=2.0)]

    [obs] = normalize_rows(IPC, rows)

    assert obs["value"] == Decimal("2.0")


def test_upsert_executes_one_statement_per_batch():
    session = MagicMock()

    upsert_observations(session, [_obs(i) for i in range(2500)], batch_size=1000)

    assert session.execute.call_count == 3
    session.commit.assert_not_called()


def test_upsert_counts_inserted_and_updated():
    session = MagicMock()
    session.execute.return_value.all.return_value = [(True,), (False,), (True,)]

    result = upsert_observations(session, [_obs(i) for i in range(3)])

    assert result == UpsertResult(inserted=2, updated=1)


def test_upsert_with_empty_rows_does_nothing():
    session = MagicMock()

    assert upsert_observations(session, []) == UpsertResult(inserted=0, updated=0)
    session.execute.assert_not_called()


def test_upsert_statement_targets_unique_constraint_and_returns_insert_flag():
    session = MagicMock()

    upsert_observations(session, [_obs(1)])

    stmt = session.execute.call_args[0][0]
    sql = str(stmt.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT ON CONSTRAINT uq_indec_observation_key DO UPDATE" in sql
    assert "xmax = 0" in sql


def test_normalize_drops_non_numeric_value_rows():
    # Un valor como "s/d" o "1,5" no debe tirar abajo todo el lote
    rows = [_ipc_row(valor=v, periodo=f"2026{m:02d}") for m, v in enumerate(["s/d", "", "1,5"], start=1)]
    rows.append(_ipc_row(valor=3.3, periodo="202604"))

    result = normalize_rows(IPC, rows)

    assert [o["period"] for o in result] == [date(2026, 4, 1)]


def test_normalize_drops_non_finite_values():
    rows = [
        _ipc_row(valor="NaN", periodo="202601"),
        _ipc_row(valor="Infinity", periodo="202602"),
        _ipc_row(valor=float("nan"), periodo="202603"),
        _ipc_row(valor=1.0, periodo="202604"),
    ]

    result = normalize_rows(IPC, rows)

    assert [o["period"] for o in result] == [date(2026, 4, 1)]


def test_normalize_drops_rows_missing_required_columns():
    broken = _ipc_row()
    del broken["codigo"]

    assert normalize_rows(IPC, [broken, _ipc_row(periodo="202609")]) == normalize_rows(
        IPC, [_ipc_row(periodo="202609")]
    )


def test_normalize_reports_dropped_rows_and_conflicting_duplicates(capsys):
    rows = [
        _ipc_row(valor=None, periodo="202601"),                     # descartada
        _ipc_row(valor=1.0, periodo="202602"),
        _ipc_row(valor=2.0, periodo="202602"),                      # duplicada con otro valor
        _ipc_row(valor=5.0, periodo="202603"),
        _ipc_row(valor=5.0, periodo="202603"),                      # duplicada idéntica
    ]

    normalize_rows(IPC, rows)

    out = capsys.readouterr().out
    assert "1 descartadas" in out
    assert "2 duplicadas" in out
    assert "1 con valores distintos" in out


def test_upsert_statement_only_updates_changed_rows():
    # Sin esto, cada corrida diaria reescribe toda la ventana de 3 meses y
    # ingested_at pierde sentido (sería "última vez vista").
    session = MagicMock()

    upsert_observations(session, [_obs(1)])

    sql = str(session.execute.call_args[0][0].compile(dialect=postgresql.dialect()))
    assert "IS DISTINCT FROM" in sql


def test_upsert_reports_unchanged_rows():
    session = MagicMock()
    session.execute.return_value.all.return_value = [(True,)]  # solo 1 fila cambió

    result = upsert_observations(session, [_obs(i) for i in range(3)])

    assert result == UpsertResult(inserted=1, updated=0, unchanged=2)


def test_normalize_keeps_the_reference_unit_description():
    row = _ipc_row(
        tipo_de_indicador="Precio promedio",
        tipo_de_indicador_descripcion="Valor por 390 g",
    )

    [obs] = normalize_rows(IPC, [row])

    assert obs["indicator_description"] == "Valor por 390 g"


def test_normalize_leaves_description_none_when_missing():
    [obs] = normalize_rows(IPC, [_ipc_row()])

    assert obs["indicator_description"] is None


def test_upsert_updates_rows_whose_description_changed():
    # Permite completar la unidad en filas ya cargadas con un --full
    session = MagicMock()

    upsert_observations(session, [_obs(1)])

    sql = str(session.execute.call_args[0][0].compile(dialect=postgresql.dialect()))
    assert "indicator_description IS DISTINCT FROM" in sql
    assert "indicator_description=excluded.indicator_description" in sql.replace(" ", "")


def _mayorista_row(**overrides):
    row = {
        "indicador": "IPIM", "clasificador": "CIIU3", "nivel": "División",
        "codigo_apertura": "15", "descripcion": "Alimentos y bebidas", "periodo": "202609",
        "tipo_de_indicador": "Indice", "tipo_de_indicador_descripcion": "Nivel del período, base dic-15=100",
        "region": "Total del país", "unidad_de_medida": "Unidad", "valor": 250.5, "observaciones": "* Dato provisorio",
    }
    row.update(overrides)
    return row


MAYORISTA = DatasetSpec(
    slug="sipm_precios_mayoristas", slices=({},), has_region=True, order="periodo.asc",
    code_column="codigo_apertura", indicator_column="indicador",
)


def test_normalize_reads_the_code_from_the_configured_column():
    [obs] = normalize_rows(MAYORISTA, [_mayorista_row()])

    assert obs["series_code"] == "15"
    assert obs["region"] == "Total del país"


def test_normalize_stores_the_indicator_when_the_spec_asks_for_it():
    [obs] = normalize_rows(MAYORISTA, [_mayorista_row()])
    assert obs["indicator"] == "IPIM"


def test_normalize_leaves_indicator_empty_for_standard_datasets():
    [obs] = normalize_rows(IPC, [_ipc_row()])
    assert obs["indicator"] == ""


def test_normalize_keeps_rows_that_only_differ_by_indicator():
    # IPP, IPIB e IPIM comparten códigos: sin `indicador` en la clave se pisarían
    rows = [_mayorista_row(indicador="IPIM", valor=1), _mayorista_row(indicador="IPP", valor=2)]

    result = normalize_rows(MAYORISTA, rows)

    assert {(o["indicator"], o["value"]) for o in result} == {("IPIM", Decimal("1")), ("IPP", Decimal("2"))}


def test_normalize_applies_the_reshape_before_mapping():
    spec = DatasetSpec(
        slug="x", slices=({},), has_region=False, order="periodo.asc",
        reshape=lambda rows: [_ipc_row(valor=r["a"]) for r in rows],
    )

    [obs] = normalize_rows(spec, [{"a": 7.5}])

    assert obs["value"] == Decimal("7.5")


def test_upsert_statement_includes_indicator_in_the_conflict_handling():
    session = MagicMock()
    upsert_observations(session, [dict(_obs(1), indicator="IPIM")])

    sql = str(session.execute.call_args[0][0].compile(dialect=postgresql.dialect()))
    assert "indicator" in sql
