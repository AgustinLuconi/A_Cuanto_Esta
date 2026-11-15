"""
Reordenamientos de datasets del INDEC que no vienen en el formato largo estándar.

Una función de reordenamiento recibe las filas crudas de la API y devuelve filas
con las columnas estándar (`clasificador`, `nivel`, `codigo`, `descripcion`,
`periodo`, `tipo_de_indicador`, `unidad_de_medida`, `valor`...), que después
procesa el cargador como a cualquier otro dataset.
"""

_COMPONENTS = {"bys": "Bienes y servicios", "cuid": "Cuidado", "tot": "Total"}
_AGE_GROUPS = {
    "men1": "Menor de 1 año",
    "1a3": "1 a 3 años",
    "4a5": "4 a 5 años",
    "6a12": "6 a 12 años",
}


def reshape_canasta_crianza(rows: list[dict]) -> list[dict]:
    """
    `canasta-crianza` viene en formato ancho: una fila por mes con 12 columnas de
    valores (`bys_men1`, `cuid_1a3`, `tot_6a12`...). Se pasa a una fila por
    (componente, tramo de edad). Los meses sin dato (`valor` nulo) se descartan.
    """
    long_rows: list[dict] = []
    for row in rows:
        for comp_key, comp_label in _COMPONENTS.items():
            for age_key, age_label in _AGE_GROUPS.items():
                code = f"{comp_key}_{age_key}"
                value = row.get(code)
                if value is None:
                    continue
                long_rows.append(
                    {
                        "clasificador": "Canasta de crianza",
                        "nivel": age_label,
                        "codigo": code,
                        "descripcion": f"{comp_label} · {age_label}",
                        "periodo": row.get("Periodo"),
                        "tipo_de_indicador": "Canasta",
                        "tipo_de_indicador_descripcion": "Valor mensual en pesos",
                        "region": None,
                        "unidad_de_medida": "Pesos argentinos",
                        "valor": value,
                        "observaciones": None,
                    }
                )
    return long_rows
