"""Schemas Pydantic de los endpoints de datos del INDEC."""
from datetime import date

from pydantic import BaseModel, ConfigDict


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dataset: str
    classifier: str
    level: str
    indicator: str  # indicador de origen (mayorista: IPP/IPIB/IPIM); '' si el dataset no lo usa
    series_code: str
    series_name: str
    region: str
    indicator_type: str
    unit: str | None = None
    period: date
    value: float


class LatestPoint(BaseModel):
    period: date
    value: float


class FoodVsWages(BaseModel):
    """IPC Alimentos vs. índice de salarios, ambos reescalados a base 100."""

    labels: list[str]  # "YYYY-MM"
    ipc_alimentos: list[float]
    salarios: list[float]


class WholesaleVsRetail(BaseModel):
    """Precios mayoristas de alimentos vs. IPC Alimentos al consumidor, ambos en base 100."""

    labels: list[str]  # "YYYY-MM"
    mayorista_alimentos: list[float]
    ipc_alimentos: list[float]


class ChildCostGroup(BaseModel):
    label: str  # tramo de edad, ej. "1 a 3 años"
    bienes_servicios: float
    cuidado: float
    total: float


class ChildCost(BaseModel):
    """Costo mensual de criar a un hijo por tramo de edad (pesos)."""

    period: date
    groups: list[ChildCostGroup]


class IndecOverview(BaseModel):
    """Último dato de las series que muestra la pantalla de economía.

    Todos los campos son opcionales: con la tabla vacía (o series faltantes)
    la API responde con `null`, nunca con error.
    """

    ipc_general_mensual: LatestPoint | None = None
    ipc_general_interanual: LatestPoint | None = None
    ipc_alimentos_mensual: LatestPoint | None = None
    ipc_alimentos_interanual: LatestPoint | None = None
    cba: LatestPoint | None = None
    cbt: LatestPoint | None = None
    ice: LatestPoint | None = None
    food_vs_wages: FoodVsWages | None = None
    wholesale_vs_retail: WholesaleVsRetail | None = None
    child_cost: ChildCost | None = None


class PriceReferenceItemOut(BaseModel):
    """Un artículo del cruce INDEC vs. supermercados, todo en el tamaño de referencia del INDEC."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str
    reference_unit: str  # "kg", "500 g", "1,5 litros"
    indec_period: date
    indec_price: float
    ours_median: float
    ours_p25: float  # la mitad central de los productos va de p25 a p75
    ours_p75: float
    diff_pct: float  # 0.1 = nuestros supermercados un 10% más caros que el INDEC
    n_offers: int
    n_products: int
    n_supermarkets: int
