"""
Schemas de Pydantic para Indicadores Económicos
"""
from pydantic import BaseModel, Field, UUID4
from datetime import datetime, date
from typing import Optional
from decimal import Decimal
from app.models.economic_indicator import IndicatorType, DataSource


class EconomicIndicatorBase(BaseModel):
    """Schema base para Indicador Económico"""
    indicator_type: IndicatorType
    value: Decimal = Field(..., decimal_places=4)
    category: Optional[str] = Field(None, max_length=100)
    date: date
    source: DataSource
    metadata_json: Optional[str] = Field(None, max_length=1000)


class EconomicIndicatorCreate(EconomicIndicatorBase):
    """Schema para crear Indicador Económico"""
    pass


class EconomicIndicatorUpdate(BaseModel):
    """Schema para actualizar Indicador Económico"""
    value: Optional[Decimal] = Field(None, decimal_places=4)
    category: Optional[str] = Field(None, max_length=100)
    metadata_json: Optional[str] = Field(None, max_length=1000)


class EconomicIndicatorInDB(EconomicIndicatorBase):
    """Schema de Indicador en base de datos"""
    id: UUID4
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EconomicIndicator(EconomicIndicatorInDB):
    """Schema de respuesta de Indicador"""
    
    class Config:
        from_attributes = True


class InflationData(BaseModel):
    """Schema para datos de inflación"""
    monthly: Decimal
    yearly: Decimal
    date: date
    source: DataSource


class DollarRates(BaseModel):
    """Schema para cotizaciones del dólar"""
    oficial: Decimal
    blue: Decimal
    mep: Optional[Decimal] = None
    ccl: Optional[Decimal] = None
    last_updated: datetime


class EconomicContext(BaseModel):
    """Schema para contexto económico general"""
    inflation_monthly: Optional[Decimal] = None
    inflation_yearly: Optional[Decimal] = None
    dollar_blue: Optional[Decimal] = None
    dollar_oficial: Optional[Decimal] = None
    dollar_mayorista: Optional[Decimal] = None
    dollar_mep: Optional[Decimal] = None
    dollar_ccl: Optional[Decimal] = None
    dollar_cripto: Optional[Decimal] = None
    dollar_tarjeta: Optional[Decimal] = None
    uva_index: Optional[Decimal] = None
    plazo_fijo_rate: Optional[Decimal] = None
    risk_country: Optional[Decimal] = None
    last_updated: datetime
    # Campos de variación para badges
    inflation_monthly_change: Optional[Decimal] = None   # pp vs. mes anterior
    inflation_monthly_date: Optional[date] = None        # fecha del último dato INDEC
    dollar_blue_change: Optional[Decimal] = None         # % vs. registro anterior
    dollar_oficial_change: Optional[Decimal] = None      # % vs. registro anterior
    dollar_mayorista_change: Optional[Decimal] = None    # % vs. registro anterior
    dollar_mep_change: Optional[Decimal] = None          # % vs. registro anterior
    dollar_ccl_change: Optional[Decimal] = None          # % vs. registro anterior
    dollar_cripto_change: Optional[Decimal] = None       # % vs. registro anterior
    dollar_tarjeta_change: Optional[Decimal] = None      # % vs. registro anterior
    risk_country_change: Optional[Decimal] = None        # % vs. registro anterior
    inflation_ytd: Optional[Decimal] = None              # acumulado año corriente (compuesto)

    class Config:
        from_attributes = True


class IPCCategory(BaseModel):
    """Schema para IPC por categoría"""
    category: str
    value: Decimal
    date: date
    variation_monthly: Optional[Decimal] = None
    variation_yearly: Optional[Decimal] = None


class EconomicSummary(BaseModel):
    """Schema para resumen económico completo"""
    context: EconomicContext
    dollar_rates: DollarRates
    inflation: InflationData
    ipc_categories: list[IPCCategory] = Field(default_factory=list)
