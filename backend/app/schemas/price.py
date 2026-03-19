"""
Schemas de Pydantic para Historial de Precios
"""
from pydantic import BaseModel, Field, UUID4
from datetime import datetime
from typing import Optional
from decimal import Decimal
from app.models.price_history import Supermarket


class PriceHistoryBase(BaseModel):
    """Schema base para Historial de Precios"""
    product_id: UUID4
    supermarket: Supermarket
    price: Decimal = Field(..., ge=0, decimal_places=2)
    was_on_sale: bool = False
    original_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    url: Optional[str] = Field(None, max_length=500)
    in_stock: bool = True


class PriceHistoryCreate(PriceHistoryBase):
    """Schema para crear registro de precio"""
    scraped_at: Optional[datetime] = None


class PriceHistoryUpdate(BaseModel):
    """Schema para actualizar registro de precio"""
    price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    was_on_sale: Optional[bool] = None
    original_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    in_stock: Optional[bool] = None


class PriceHistoryInDB(PriceHistoryBase):
    """Schema de Precio en base de datos"""
    id: UUID4
    scraped_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class PriceHistory(PriceHistoryInDB):
    """Schema de respuesta de Precio"""
    effective_price: float
    saved_amount: float
    
    class Config:
        from_attributes = True


class CurrentPrice(BaseModel):
    """Schema para precio actual de un producto en un supermercado"""
    supermarket: Supermarket
    price: Decimal
    was_on_sale: bool
    original_price: Optional[Decimal] = None
    discount_percentage: Optional[Decimal] = None
    url: Optional[str] = None
    last_updated: datetime
    in_stock: bool
    
    class Config:
        from_attributes = True


class PriceComparison(BaseModel):
    """Schema para comparación de precios entre supermercados"""
    product_id: UUID4
    product_name: str
    prices: list[CurrentPrice]
    lowest_price: Decimal
    highest_price: Decimal
    price_difference: Decimal
    price_difference_percentage: Decimal
    best_deal: Supermarket
    
    class Config:
        from_attributes = True


class PriceTrend(BaseModel):
    """Schema para tendencia de precio"""
    date: datetime
    price: Decimal
    was_on_sale: bool
    
    class Config:
        from_attributes = True


class PriceEvolution(BaseModel):
    """Schema para evolución de precios de un producto"""
    product_id: UUID4
    product_name: str
    supermarket: Supermarket
    history: list[PriceTrend]
    current_price: Decimal
    price_change_7d: Optional[Decimal] = None
    price_change_30d: Optional[Decimal] = None
    average_price: Decimal
    min_price: Decimal
    max_price: Decimal
    
    class Config:
        from_attributes = True
