"""
Pruebas unitarias para app/utils/location_utils.py:
mapeo Provincia -> Región y funciones de validación/display usadas en
filtros geográficos de precios.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.location_utils import (
    get_region_from_province,
    validate_location,
    get_province_display_name,
    get_region_display_name,
)


def test_get_region_from_province_maps_caba_and_buenos_aires_to_amba():
    assert get_region_from_province("caba") == "amba"
    assert get_region_from_province("buenos_aires") == "amba"


def test_get_region_from_province_maps_cordoba_to_pampeana_primary_region():
    # Córdoba pertenece a PAMPEANA y CENTRO, pero el mapeo primario es PAMPEANA
    assert get_region_from_province("cordoba") == "pampeana"


def test_get_region_from_province_is_case_and_whitespace_insensitive():
    assert get_region_from_province(" Mendoza ") == "cuyo"


def test_get_region_from_province_returns_none_for_unknown_province():
    assert get_region_from_province("narnia") is None


def test_get_region_from_province_returns_none_for_empty_string():
    assert get_region_from_province("") is None
    assert get_region_from_province(None) is None


def test_validate_location_true_when_province_matches_region():
    assert validate_location("salta", "noa") is True


def test_validate_location_false_when_province_does_not_match_region():
    assert validate_location("salta", "cuyo") is False


def test_validate_location_true_when_province_or_region_missing():
    # NULL/vacío es válido según la docstring (no se puede validar lo que falta)
    assert validate_location("", "noa") is True
    assert validate_location("salta", "") is True
    assert validate_location(None, None) is True


def test_validate_location_false_when_province_unrecognized_but_region_given():
    # Provincia inexistente -> get_region_from_province devuelve None -> inválido
    assert validate_location("narnia", "amba") is False


def test_get_province_display_name_formats_known_code():
    assert get_province_display_name("santiago_del_estero") == "Santiago Del Estero"


def test_get_province_display_name_falls_back_for_unknown_code():
    assert get_province_display_name("atlantida") == "Atlantida"


def test_get_province_display_name_handles_empty_value():
    assert get_province_display_name("") == "Sin especificar"


def test_get_region_display_name_uses_lookup_table():
    assert get_region_display_name("noa") == "Noroeste Argentino"
    assert get_region_display_name("amba") == "Área Metropolitana Buenos Aires"


def test_get_region_display_name_falls_back_to_title_case_for_unknown_code():
    assert get_region_display_name("desconocida") == "Desconocida"


def test_get_region_display_name_handles_empty_value():
    assert get_region_display_name("") == "Sin especificar"
