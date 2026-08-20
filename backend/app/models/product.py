"""
Modelo de base de datos para Productos
"""
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.config.database import Base


class ProductCategory(str, enum.Enum):
    """Categorías de productos"""
    ALIMENTOS = "alimentos"
    BEBIDAS = "bebidas"
    LIMPIEZA = "limpieza"
    HIGIENE_PERSONAL = "higiene_personal"
    LACTEOS = "lacteos"
    CARNES = "carnes"
    FRUTAS_VERDURAS = "frutas_verduras"
    PANADERIA = "panaderia"
    CONGELADOS = "congelados"
    SNACKS = "snacks"
    DESAYUNO = "desayuno"
    MASCOTAS = "mascotas"
    BEBES = "bebes"
    HOGAR_BAZAR = "hogar_bazar"
    FARMACIA_SALUD = "farmacia_salud"
    ELECTRO_TECNOLOGIA = "electro_tecnologia"
    OTROS = "otros"


class ProductUnit(str, enum.Enum):
    """Unidades de medida"""
    KG = "kg"
    G = "g"
    L = "l"
    ML = "ml"
    UNIDAD = "unidad"
    PACK = "pack"


class Product(Base):
    """
    Modelo de Producto.
    Representa el catálogo maestro de productos.
    """
    __tablename__ = "products"
    
    # Identificador único
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Información del producto
    name = Column(String(255), nullable=False, index=True)
    normalized_name = Column(String(255), nullable=False, index=True)  # Para búsquedas
    brand = Column(String(100), index=True)
    category = Column(SQLEnum(ProductCategory), nullable=False, index=True)
    
    # Presentación
    unit = Column(SQLEnum(ProductUnit), nullable=False)
    quantity = Column(String(50))  # Ej: "900", "1.5", "pack x 6"
    
    # Información adicional
    description = Column(String(500))
    image_url = Column(String(500))
    barcode = Column(String(50), unique=True, index=True)  # EAN/UPC si está disponible
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', brand='{self.brand}')>"
    
    @property
    def full_name(self) -> str:
        """Nombre completo del producto"""
        parts = [self.brand, self.name]
        if self.quantity:
            parts.append(f"({self.quantity} {self.unit.value})")
        return " ".join(filter(None, parts))
