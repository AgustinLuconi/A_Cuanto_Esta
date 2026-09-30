"""
Endpoints de Notificaciones Push (Web Push API) y Alertas de Precio.

GET    /api/v1/push/vapid-public-key  — clave pública VAPID (no es secreta)
POST   /api/v1/push/subscribe         — alta/actualización de suscripción + alertas
GET    /api/v1/push/alerts            — alertas de una suscripción (?endpoint=)
DELETE /api/v1/push/alerts/{alert_id} — borra una alerta puntual
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings
from app.models.price_alert import PriceAlert
from app.models.product import Product
from app.models.push_subscription import PushSubscription
from app.schemas import push as schemas_push

router = APIRouter()


@router.get("/vapid-public-key", response_model=schemas_push.VapidPublicKeyResponse)
def get_vapid_public_key():
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="Push notifications no configuradas")
    return schemas_push.VapidPublicKeyResponse(public_key=settings.VAPID_PUBLIC_KEY)


@router.post("/subscribe", response_model=schemas_push.SubscribeResponse)
def subscribe(body: schemas_push.SubscribeRequest, db: Session = Depends(get_db)):
    # Validar los product_id ANTES de tocar la suscripción: en Postgres (Neon)
    # un product_id inexistente rompería la FK de PriceAlert con un
    # IntegrityError no capturado (500 crudo); acá lo convertimos en un 404
    # limpio y no dejamos una suscripción a medio crear si falla.
    requested_product_ids = {alert_in.product_id for alert_in in body.alerts}
    if requested_product_ids:
        existing_ids = {
            pid for (pid,) in db.query(Product.id).filter(Product.id.in_(requested_product_ids)).all()
        }
        missing = requested_product_ids - existing_ids
        if missing:
            raise HTTPException(status_code=404, detail=f"Producto(s) no encontrado(s): {missing}")

    subscription = (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint == body.subscription.endpoint)
        .first()
    )
    if subscription is None:
        subscription = PushSubscription(
            endpoint=body.subscription.endpoint,
            p256dh_key=body.subscription.keys.p256dh,
            auth_key=body.subscription.keys.auth,
        )
        db.add(subscription)
        db.flush()  # asigna subscription.id sin cerrar la transacción
    else:
        # Las keys pueden rotar si el browser renueva la suscripción con el mismo endpoint.
        subscription.p256dh_key = body.subscription.keys.p256dh
        subscription.auth_key = body.subscription.keys.auth

    for alert_in in body.alerts:
        existing = (
            db.query(PriceAlert)
            .filter(
                PriceAlert.subscription_id == subscription.id,
                PriceAlert.product_id == alert_in.product_id,
            )
            .first()
        )
        if existing:
            existing.target_price = alert_in.target_price
            existing.notified_at_price = None  # nuevo umbral -> hay que poder re-notificar
        else:
            db.add(PriceAlert(
                subscription_id=subscription.id,
                product_id=alert_in.product_id,
                target_price=alert_in.target_price,
            ))

    db.commit()
    db.refresh(subscription)

    all_alerts = (
        db.query(PriceAlert)
        .filter(PriceAlert.subscription_id == subscription.id)
        .all()
    )
    return schemas_push.SubscribeResponse(
        subscription_id=subscription.id,
        alerts=[schemas_push.PriceAlertOut.model_validate(a) for a in all_alerts],
    )


@router.get("/alerts", response_model=list[schemas_push.PriceAlertOut])
def list_alerts(endpoint: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    subscription = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    if subscription is None:
        return []
    alerts = db.query(PriceAlert).filter(PriceAlert.subscription_id == subscription.id).all()
    return [schemas_push.PriceAlertOut.model_validate(a) for a in alerts]


@router.delete("/alerts/{alert_id}", status_code=204)
def delete_alert(alert_id: UUID, db: Session = Depends(get_db)) -> None:
    db.query(PriceAlert).filter(PriceAlert.id == alert_id).delete()
    db.commit()
