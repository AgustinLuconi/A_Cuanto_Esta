"""
Acceso a datos del cruce de precios INDEC vs. supermercados.

Lee de la base propia: `indec_observations` (precios promedio del INDEC, GBA) y
`price_history` + `products` (ofertas frescas de los supermercados).
"""
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.indec_observation import IndecObservation
from app.models.price_history import STALE_THRESHOLD_HOURS, PriceHistory
from app.models.product import Product
from app.services.indec.price_reference import (
    IndecPoint,
    Offer,
    ReferenceItem,
    assemble_price_reference,
)
from app.services.indec.reference_rules import RULES, ReferenceRule
from app.utils.time import utcnow_aware

# La consulta recorre varios días de historial de precios: se cachea en memoria.
# Los datos cambian como mucho una vez por día (scraping) o por mes (INDEC).
CACHE_TTL = timedelta(minutes=30)
_cache: dict = {}  # {"at": datetime, "value": list[ReferenceItem]}


def fetch_indec_points(db: Session, rules: tuple[ReferenceRule, ...]) -> dict[str, IndecPoint]:
    """
    Último precio promedio (GBA) del INDEC de cada artículo con regla. Ignora filas
    sin unidad de referencia (cargadas antes de guardarla): no se pueden comparar.
    """
    points: dict[str, IndecPoint] = {}
    for rule in rules:
        row = (
            db.query(IndecObservation)
            .filter(
                IndecObservation.dataset == "ipc_nacional",
                IndecObservation.indicator_type == "Precio promedio",
                IndecObservation.region == "GBA",
                IndecObservation.series_code == rule.indec_code,
                IndecObservation.indicator_description.isnot(None),
            )
            .order_by(IndecObservation.period.desc())
            .first()
        )
        if row is not None:
            points[rule.indec_code] = IndecPoint(
                code=rule.indec_code,
                price=Decimal(row.value),
                description=row.indicator_description,
                period=row.period,
            )
    return points


def fetch_fresh_offers(db: Session, now: datetime | None = None) -> list[Offer]:
    """
    Una oferta por (producto, supermercado): el precio MÁS NUEVO dentro de las
    últimas STALE_THRESHOLD_HOURS horas, y solo si está en stock y es mayor a 0.
    Se elige primero el más nuevo y recién después se descartan las inválidas, para
    que un precio viejo válido no tape uno nuevo roto.
    """
    now = now or utcnow_aware()
    cutoff = now - timedelta(hours=STALE_THRESHOLD_HOURS)
    rows = (
        db.query(
            Product.id,
            Product.name,
            Product.normalized_name,
            Product.quantity,
            PriceHistory.supermarket,
            PriceHistory.price,
            PriceHistory.in_stock,
        )
        .join(PriceHistory, PriceHistory.product_id == Product.id)
        .filter(PriceHistory.scraped_at >= cutoff)
        .order_by(PriceHistory.scraped_at.desc())
        .all()
    )
    offers: list[Offer] = []
    seen: set[tuple] = set()
    for pid, name, normalized, quantity, supermarket, price, in_stock in rows:
        key = (pid, supermarket)
        if key in seen:
            continue  # ya tomamos el más nuevo de este producto en este supermercado
        seen.add(key)
        if not in_stock or price is None or price <= 0:
            continue
        offers.append(
            Offer(
                product_id=str(pid),
                name=name,
                supermarket=supermarket.name,
                price=Decimal(price),
                quantity=quantity,
                normalized_name=normalized,
            )
        )
    return offers


def get_price_reference(
    db: Session, now: datetime | None = None, rules: tuple[ReferenceRule, ...] = RULES
) -> list[ReferenceItem]:
    """Cruce completo INDEC vs. supermercados, cacheado CACHE_TTL."""
    now = now or utcnow_aware()
    cached = _cache.get("value")
    if cached is not None and now - _cache["at"] < CACHE_TTL:
        return cached
    items = assemble_price_reference(
        rules, fetch_indec_points(db, rules), fetch_fresh_offers(db, now)
    )
    _cache["at"], _cache["value"] = now, items
    return items
