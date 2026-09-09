"""
Modelo de base de datos para Suscripciones de Web Push.

No hay cuentas de usuario en el proyecto: cada suscripción representa un
navegador/dispositivo (el `endpoint` que da el browser es único por
combinación navegador+dispositivo+origen), no una persona.
"""
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.config.database import Base
from app.utils.time import utcnow_aware


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    endpoint   = Column(String(500), nullable=False, unique=True, index=True)
    p256dh_key = Column(String(255), nullable=False)
    auth_key   = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow_aware, nullable=False)

    alerts = relationship("PriceAlert", back_populates="subscription", cascade="all, delete-orphan")
