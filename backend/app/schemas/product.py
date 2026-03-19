"""
Schemas de Pydantic para Producto
"""
from pydantic import BaseModel, Field, UUID4
from datetime import datetime
from typing import Optional
from app.models.product import ProductCategory, ProductUnit


class ProductBase(BaseModel):
    """Schema base para Producto"""
    name: str = Field(..., min_length=1, max_length=255)
    normalized_name: str = Field(..., min_length=1, max_length=255)
    brand: Optional[str] = Field(None, max_length=100)
    category: ProductCategory
    unit: ProductUnit
    quantity: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    barcode: Optional[str] = Field(None, max_length=50)


class ProductCreate(ProductBase):
    """Schema para crear Producto"""
    pass


class ProductUpdate(BaseModel):
    """Schema para actualizar Producto"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    normalized_name: Optional[str] = Field(None, min_length=1, max_length=255)
    brand: Optional[str] = Field(None, max_length=100)
    category: Optional[ProductCategory] = None
    unit: Optional[ProductUnit] = None
    quantity: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    barcode: Optional[str] = Field(None, max_length=50)


class ProductInDB(ProductBase):
    """Schema de Producto en base de datos"""
    id: UUID4
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Product(ProductInDB):
    """Schema de respuesta de Producto"""
    full_name: str
    
    class Config:
        from_attributes = True


class ProductWithPrices(Product):
    """Schema de Producto con precios actuales"""
    current_prices: list = Field(default_factory=list)
    lowest_price: Optional[float] = None
    highest_price: Optional[float] = None
    price_difference: Optional[float] = None
    
    class Config:
        from_attributes = True
