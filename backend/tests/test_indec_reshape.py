"""
Pruebas del reordenamiento de `canasta-crianza`: viene en formato ancho (una fila
por mes con 12 columnas de valores) y se pasa a filas largas estándar.
"""
from app.services.indec.reshape import reshape_canasta_crianza

ROW = {
    "anio": 2026, "Mes": 9, "Periodo": "202609",
    "bys_men1": 184911.53, "bys_men1_null": None,
    "cuid_men1": 385920.04, "cuid_men1_null": None,
    "tot_men1": 570831.58, "tot_men1_null": None,
    "bys_1a3": 238764.09, "bys_1a3_null": None,
    "cuid_1a3": 441051.48, "cuid_1a3_null": None,
    "tot_1a3": 679815.57, "tot_1a3_null": None,
    "bys_4a5": 304094.69, "bys_4a5_null": None,
    "cuid_4a5": 275657.17, "cuid_4a5_null": None,
    "tot_4a5": 579751.87, "tot_4a5_null": None,
    "bys_6a12": 377230.63, "bys_6a12_null": None,
    "cuid_6a12": 351618.96, "cuid_6a12_null": None,
    "tot_6a12": 728849.59, "tot_6a12_null": None,
}


def test_each_month_becomes_twelve_long_rows():
    rows = reshape_canasta_crianza([ROW])

    assert len(rows) == 12
    assert {r["codigo"] for r in rows} == {
        f"{c}_{g}" for c in ("bys", "cuid", "tot") for g in ("men1", "1a3", "4a5", "6a12")
    }


def test_long_rows_use_the_standard_raw_columns():
    rows = {r["codigo"]: r for r in reshape_canasta_crianza([ROW])}
    total = rows["tot_men1"]

    assert total["periodo"] == "202609"          # "Periodo" pasa a "periodo"
    assert total["valor"] == 570831.58
    assert total["clasificador"] == "Canasta de crianza"
    assert total["nivel"] == "Menor de 1 año"
    assert total["descripcion"] == "Total · Menor de 1 año"
    assert total["tipo_de_indicador"] == "Canasta"
    assert total["unidad_de_medida"] == "Pesos argentinos"
    assert "region" not in total or total["region"] is None
    assert rows["bys_6a12"]["descripcion"] == "Bienes y servicios · 6 a 12 años"
    assert rows["cuid_4a5"]["descripcion"] == "Cuidado · 4 a 5 años"


def test_null_values_are_dropped():
    row = dict(ROW, tot_men1=None, tot_men1_null="///")

    codes = {r["codigo"] for r in reshape_canasta_crianza([row])}

    assert "tot_men1" not in codes
    assert len(codes) == 11


def test_reshape_of_no_rows_is_empty():
    assert reshape_canasta_crianza([]) == []
