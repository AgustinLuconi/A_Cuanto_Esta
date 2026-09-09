"""
Schemas de Pydantic para Notificaciones Push (Web Push API) y Alertas de Precio.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, UUID4


class PushSubscriptionKeys(BaseModel):
    """Claves de cifrado de una PushSubscription del navegador."""
    p256dh: str
    auth: str


class PushSubscriptionInfo(BaseModel):
    """Forma exacta de `PushSubscription.toJSON()` en el navegador."""
    endpoint: str = Field(..., max_length=500)
    keys: PushSubscriptionKeys


class AlertCreate(BaseModel):
    product_id: UUID4
    target_price: Decimal = Field(..., gt=0, decimal_places=2)


class SubscribeRequest(BaseModel):
    """Alta/actualización de una suscripción y (opcionalmente) sus alertas.
    Sirve tanto para suscribir + crear la primera alerta de un producto,
    como para la migración en bloque de alertas viejas de localStorage."""
    subscription: PushSubscriptionInfo
    alerts: list[AlertCreate] = []


class PriceAlertOut(BaseModel):
    id: UUID4
    product_id: UUID4
    target_price: Decimal
    created_at: datetime
    notified_at_price: Decimal | None = None

    class Config:
        from_attributes = True


class SubscribeResponse(BaseModel):
    subscription_id: UUID4
    alerts: list[PriceAlertOut]


class VapidPublicKeyResponse(BaseModel):
    public_key: str
