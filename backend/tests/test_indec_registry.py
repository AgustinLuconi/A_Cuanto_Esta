"""Pruebas del registro declarativo de datasets del INDEC."""
import pytest

from app.services.indec.registry import REGISTRY, DatasetSpec, get_specs


def test_registry_has_the_three_v1_datasets():
    assert set(REGISTRY) == {
        "ipc_nacional",
        "valorizacion_canastas_cba_cbt",
        "indice_salarios",
        "canasta-crianza",
        "sipm_precios_mayoristas",
    }


def test_get_specs_none_returns_all():
    specs = get_specs(None)
    assert {s.slug for s in specs} == set(REGISTRY)
    assert all(isinstance(s, DatasetSpec) for s in specs)


def test_get_specs_unknown_slug_raises_value_error_listing_valid_slugs():
    with pytest.raises(ValueError) as exc_info:
        get_specs("no_existe")

    message = str(exc_info.value)
    for slug in REGISTRY:
        assert slug in message


def test_order_includes_region_only_when_dataset_has_region():
    for spec in REGISTRY.values():
        assert ("region.asc" in spec.order) == spec.has_region
    assert REGISTRY["indice_salarios"].has_region is False


def test_ipc_slices_match_spec():
    slices = REGISTRY["ipc_nacional"].slices
    assert slices == (
        {
            "clasificador": "in.(IPC,COICOP Argentina 2019)",
            "codigo": "in.(0,01,01.1)",
            "tipo_de_indicador": "in.(Indice,v_m,v_ia,v_acum)",
            "region": "in.(Nacional,GBA)",
        },
        {
            "nivel": "eq.Producto",
            "tipo_de_indicador": "eq.Precio promedio",
            "region": "eq.GBA",
        },
    )


def test_every_slice_value_is_a_postgrest_filter():
    for spec in REGISTRY.values():
        for slice_ in spec.slices:
            for value in slice_.values():
                assert value.startswith(("eq.", "in.("))


def test_dataset_spec_defaults_keep_the_standard_columns():
    spec = REGISTRY["ipc_nacional"]
    assert spec.code_column == "codigo"
    assert spec.period_column == "periodo"
    assert spec.indicator_column is None
    assert spec.reshape is None


def test_mayorista_spec_uses_its_own_columns_and_indicador():
    spec = REGISTRY["sipm_precios_mayoristas"]
    assert spec.code_column == "codigo_apertura"
    assert spec.indicator_column == "indicador"   # IPP / IPIB / IPIM comparten códigos
    assert spec.has_region is True
    assert "indicador.asc" in spec.order
    # solo el indicador de precios mayoristas (IPIM), nunca los tres
    assert all(slice_["indicador"] == "eq.IPIM" for slice_ in spec.slices)


def test_crianza_spec_reshapes_wide_rows_and_uses_capitalized_period():
    spec = REGISTRY["canasta-crianza"]
    assert spec.reshape is not None
    assert spec.period_column == "Periodo"   # este dataset usa mayúscula
    assert spec.order == "Periodo.asc"
    assert spec.has_region is False
