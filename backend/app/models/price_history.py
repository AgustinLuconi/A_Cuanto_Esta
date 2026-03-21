"""
Modelo de base de datos para Historial de Precios
"""
from sqlalchemy import Column, String, Numeric, Boolean, DateTime, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.config.database import Base


class Supermarket(str, enum.Enum):
    """Supermercados soportados"""
    CARREFOUR = "carrefour"
    COTO = "coto"
    DISCO = "disco"
    ATOMO = "atomo"
    VEA   = "vea"
    JUMBO = "jumbo"


class PriceHistory(Base):
    """
    Modelo de Historial de Precios.
    Almacena cada precio registrado de cada producto en cada supermercado.
    """
    __tablename__ = "price_history"
    
    # Identificador
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relación con producto
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    # Información del precio
    supermarket = Column(SQLEnum(Supermarket), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)  # Precio en pesos argentinos
    
    # Información de oferta/descuento
    was_on_sale = Column(Boolean, default=False)
    original_price = Column(Numeric(10, 2))  # Precio original si está en oferta
    discount_percentage = Column(Numeric(5, 2))  # Porcentaje de descuento
    
    # Información del scraping
    url = Column(String(500))  # URL del producto en el sitio
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Disponibilidad
    in_stock = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relaciones
    product = relationship("Product", back_populates="price_history")
    
    # Índices compuestos para queries comunes
    __table_args__ = (
        Index('idx_product_supermarket_date', 'product_id', 'supermarket', 'scraped_at'),
        Index('idx_supermarket_date', 'supermarket', 'scraped_at'),
    )
    
    def __repr__(self):
        return f"<PriceHistory(product_id={self.product_id}, supermarket={self.supermarket.value}, price={self.price}, date={self.scraped_at})>"
    
    @property
    def effective_price(self) -> float:
        """Precio efectivo (considerando ofertas)"""
        return float(self.price)
    
    @property
    def saved_amount(self) -> float:
        """Cantidad ahorrada si está en oferta"""
        if self.was_on_sale and self.original_price:
            return float(self.original_price - self.price)
        return 0.0
