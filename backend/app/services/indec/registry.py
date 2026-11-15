"""
Registro declarativo de los datasets del INDEC que se ingieren.

Es la única parte que se edita para sumar un dataset: cada `DatasetSpec`
dice qué cortes (slices) se piden, con filtros del lado servidor, para no
bajar series que nadie usa (el IPC completo tiene 235.683 filas).

IMPORTANTE: al agregar un slice nuevo a un dataset que YA tiene datos guardados,
el modo incremental solo trae los últimos 3 meses de ese corte; hay que correr
una vez `python scripts/fetch_indec_data.py --dataset <slug> --full` (o el
workflow `indec-sync` con `full=true`) para cargar su historia completa.

Los filtros usan la sintaxis PostgREST de la API: `eq.<valor>` o `in.(a,b,c)`.
Los valores fueron verificados contra el INDEC real el 2026-11-14.
"""
from collections.abc import Callable
from dataclasses import dataclass

from app.services.indec.reshape import reshape_canasta_crianza

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
    # Los datasets no son del todo homogéneos: estos campos cubren las diferencias.
    code_column: str = "codigo"            # el mayorista lo llama `codigo_apertura`
    period_column: str = "periodo"         # nombre en el servidor (canasta-crianza: "Periodo")
    indicator_column: str | None = None    # si el dataset mezcla indicadores con los mismos códigos
    reshape: Callable[[list[dict]], list[dict]] | None = None  # para formatos no estándar


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
    # Costo mensual de criar a un hijo, por tramo de edad. Viene en formato ancho.
    "canasta-crianza": DatasetSpec(
        slug="canasta-crianza",
        slices=({},),  # 81 filas, todo útil
        has_region=False,
        order="Periodo.asc",
        period_column="Periodo",
        reshape=reshape_canasta_crianza,
    ),
    # Precios mayoristas (IPIM). El dataset completo tiene 234.260 filas de toda la
    # industria; solo se guardan los alimentos y el nivel general, que sirven como
    # indicador adelantado de los precios que pagan los supermercados.
    # IPP, IPIB e IPIM comparten códigos de serie: `indicador` entra en la clave.
    "sipm_precios_mayoristas": DatasetSpec(
        slug="sipm_precios_mayoristas",
        slices=(
            {   # divisiones de agro y de alimentos y bebidas
                "indicador": "eq.IPIM",
                "clasificador": "eq.CIIU3",
                "codigo_apertura": "in.(01,15)",
                "tipo_de_indicador": "in.(Indice,v_m,v_ia,v_acum)",
            },
            {   # nivel general
                "indicador": "eq.IPIM",
                "clasificador": "eq.SIPM 93",
                "nivel": "eq.Nivel general",
                "tipo_de_indicador": "in.(Indice,v_m,v_ia,v_acum)",
            },
        ),
        has_region=True,
        order=(
            "periodo.asc,indicador.asc,clasificador.asc,nivel.asc,"
            "codigo_apertura.asc,tipo_de_indicador.asc,region.asc"
        ),
        code_column="codigo_apertura",
        indicator_column="indicador",
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
