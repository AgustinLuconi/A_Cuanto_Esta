"""
Chequea las alertas de precio activas contra el precio actual de cada
producto y manda un Web Push real a las que ya cumplieron su objetivo.

Pensado para correr una vez al día vía GitHub Actions (ver
.github/workflows/check-price-alerts.yml) -- no hay ningún proceso
corriendo 24/7 en este proyecto (ni Celery ni un cron de Render).

Uso:
    python scripts/check_price_alerts.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import joinedload

from app.api.v1.endpoints.products import _get_current_prices_bulk
from app.config.database import SessionLocal
from app.config.settings import settings
from app.models.price_alert import PriceAlert
from app.models.push_subscription import PushSubscription

try:
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover - solo pasa si no se corrió `pip install -r requirements.txt`
    webpush = None
    WebPushException = Exception


def _due_alerts(alerts: list, prices_by_product: dict) -> list[tuple]:
    """
    Devuelve las alertas que corresponde notificar ahora, junto con el
    precio actual que dispara la notificación. Función pura (no toca la DB
    ni pywebpush) para poder testearla con datos fake -- ver
    tests/test_check_price_alerts.py.
    """
    due = []
    for alert in alerts:
        current_prices = prices_by_product.get(alert.product_id, [])
        fresh_prices = [float(ph.price) for ph in current_prices if not ph.is_stale]
        if not fresh_prices:
            continue
        lowest = min(fresh_prices)
        if lowest > float(alert.target_price):
            continue
        if alert.notified_at_price is not None and float(alert.notified_at_price) == lowest:
            continue
        due.append((alert, lowest))
    return due


def main():
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        print("VAPID_PRIVATE_KEY / VAPID_PUBLIC_KEY no configuradas -- abortando.", file=sys.stderr)
        sys.exit(1)

    session = SessionLocal()
    try:
        alerts = (
            session.query(PriceAlert)
            .options(joinedload(PriceAlert.subscription))
            .all()
        )
        if not alerts:
            print("No hay alertas activas.")
            return

        product_ids = list({a.product_id for a in alerts})
        prices_by_product = _get_current_prices_bulk(session, product_ids)
        due = _due_alerts(alerts, prices_by_product)
        print(f"{len(alerts)} alertas activas, {len(due)} para notificar.")

        expired_subscription_ids = set()
        for alert, current_price in due:
            subscription = alert.subscription
            if subscription.id in expired_subscription_ids:
                continue
            payload = json.dumps({
                "title": "¡Bajó de precio!",
                "product_id": str(alert.product_id),
                "price": current_price,
                "target_price": float(alert.target_price),
            })
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {"p256dh": subscription.p256dh_key, "auth": subscription.auth_key},
                    },
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
                    timeout=10,
                )
                alert.notified_at_price = current_price
                # Commit por alerta procesada, no al final del loop: si el
                # proceso muere a mitad de camino (timeout del runner de
                # GitHub Actions, OOM), los pushes ya enviados con éxito no
                # deben perderse -- mismo bug ya vivido y arreglado en
                # merge_coto_strict_matches.py (ver memoria del proyecto
                # coto_merge_backup_safety_2026_09_09), donde un commit único
                # al final dejó fusiones ya aplicadas sin registrar.
                session.commit()
                print(f"  OK   alerta {alert.id} (producto {alert.product_id}) -> ${current_price}")
            except WebPushException as exc:
                if exc.status_code in (404, 410):
                    print(f"  SUSCRIPCIÓN VENCIDA, se borra (subscription={subscription.id})")
                    expired_subscription_ids.add(subscription.id)
                else:
                    print(f"  ERROR alerta {alert.id}: {exc}", file=sys.stderr)
            except Exception as exc:
                # pywebpush usa requests internamente y NO envuelve errores
                # de red (timeout, conexión rechazada, etc.) en
                # WebPushException -- sin este except, uno de esos errores
                # en una sola alerta tiraría abajo main() entero sin
                # commitear el resto del progreso ya hecho.
                print(f"  ERROR DE RED alerta {alert.id}: {exc}", file=sys.stderr)

        if expired_subscription_ids:
            session.query(PushSubscription).filter(
                PushSubscription.id.in_(expired_subscription_ids)
            ).delete(synchronize_session=False)
            session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    main()
