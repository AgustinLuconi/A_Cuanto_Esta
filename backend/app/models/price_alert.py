"""
Modelo de base de datos para Alertas de Precio.

Una alerta "avisame si <product> baja de <target_price>", atada a una
PushSubscription (navegador/dispositivo) — reemplaza el localStorage que
usaba el sistema anterior.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.config.database import Base
from app.utils.time import utcnow_aware


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id   = Column(UUID(as_uuid=True), ForeignKey("push_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id        = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    target_price      = Column(Numeric(10, 2), nullable=False)
    created_at        = Column(DateTime(timezone=True), default=utcnow_aware, nullable=False)
    # Último precio con el que ya se notificó — evita re-notificar dos veces
    # al mismo precio (mismo campo/semántica que el localStorage viejo).
    notified_at_price = Column(Numeric(10, 2), nullable=True)

    subscription = relationship("PushSubscription", back_populates="alerts")
    product      = relationship("Product")

    __table_args__ = (
        UniqueConstraint("subscription_id", "product_id", name="uq_subscription_product"),
    )
