"""Schemas Pydantic de los endpoints de datos del INDEC."""
from datetime import date

from pydantic import BaseModel, ConfigDict


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dataset: str
    classifier: str
    level: str
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
