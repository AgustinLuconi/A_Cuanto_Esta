"""
Registro declarativo de los datasets del INDEC que se ingieren.

Es la única parte que se edita para sumar un dataset: cada `DatasetSpec`
dice qué cortes (slices) se piden, con filtros del lado servidor, para no
bajar series que nadie usa (el IPC completo tiene 235.683 filas).

Los filtros usan la sintaxis PostgREST de la API: `eq.<valor>` o `in.(a,b,c)`.
Los valores fueron verificados contra el INDEC real el 2026-11-14.
"""
from dataclasses import dataclass

# Claves de ordenamiento: coinciden con la restricción única de la tabla, así
# el orden es total y la paginación no solapa ni saltea filas.
_ORDER_BASE = "periodo.asc,clasificador.asc,nivel.asc,codigo.asc,tipo_de_indicador.asc"


@dataclass(frozen=True)
class DatasetSpec:
    slug: str
    # Cada slice es un conjunto de filtros que se pide por separado; el
    # resultado de todos los slices se une.
    slices: tuple[dict[str, str], ...]
    has_region: bool
    order: str


REGISTRY: dict[str, DatasetSpec] = {
    "ipc_nacional": DatasetSpec(
        slug="ipc_nacional",
        slices=(
            # Nivel general, Alimentos y bebidas y su grupo Alimentos.
            # El grupo 01.1 solo existe por región (no a nivel Nacional).
            {
                "clasificador": "in.(IPC,COICOP Argentina 2019)",
                "codigo": "in.(0,01,01.1)",
                "tipo_de_indicador": "in.(Indice,v_m,v_ia,v_acum)",
                "region": "in.(Nacional,GBA)",
            },
            # Precios promedio en pesos por producto (referencia oficial)
            {
                "nivel": "eq.Producto",
                "tipo_de_indicador": "eq.Precio promedio",
                "region": "eq.GBA",
            },
        ),
        has_region=True,
        order=f"{_ORDER_BASE},region.asc",
    ),
    "valorizacion_canastas_cba_cbt": DatasetSpec(
        slug="valorizacion_canastas_cba_cbt",
        slices=({},),  # chico (1.651 filas) y todo útil
        has_region=True,
        order=f"{_ORDER_BASE},region.asc",
    ),
    "indice_salarios": DatasetSpec(
        slug="indice_salarios",
        slices=(
            {
                "codigo": "in.(0,100,110,120,200)",
                "tipo_de_indicador": "in.(Indice,v_m,v_ia)",
            },
        ),
        has_region=False,  # el dataset no tiene columna `region`
        order=_ORDER_BASE,
    ),
}


def get_specs(slug: str | None) -> list[DatasetSpec]:
    """Todos los datasets (slug=None) o solo el pedido. ValueError si no existe."""
    if slug is None:
        return list(REGISTRY.values())
    if slug not in REGISTRY:
        valid = ", ".join(sorted(REGISTRY))
        raise ValueError(f"Dataset desconocido: {slug!r}. Válidos: {valid}")
    return [REGISTRY[slug]]
