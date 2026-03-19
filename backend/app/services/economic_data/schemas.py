"""
Schemas Pydantic para las respuestas crudas de las APIs económicas.
No son schemas de DB — solo representan la estructura JSON de cada endpoint.
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class InflationRecord(BaseModel):
    fecha: date
    valor: float


class DollarRecord(BaseModel):
    casa: str
    compra: float
    venta: float
    fecha: date


class UVARecord(BaseModel):
    fecha: date
    valor: float


class DolarAPIQuote(BaseModel):
    moneda: str
    casa: str
    nombre: str
    compra: Optional[float] = None
    venta: Optional[float] = None
    fechaActualizacion: datetime
