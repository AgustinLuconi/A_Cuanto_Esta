"""
Endpoints de Análisis.

GET /api/v1/analysis/price-vs-inflation — Comparar evolución de precio contra inflación
"""
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.economic_indicator import EconomicIndicator, IndicatorType
from app.models.price_history import PriceHistory, Supermarket
from app.models.product import Product

router = APIRouter()


class PriceInflationAnalysis(BaseModel):
    product_name: str
    supermarket: Supermarket
    period_days: int
    price_start: float
    price_end: float
    price_change_percent: float
    inflation_period_percent: float
    comparison: Literal["above", "below", "equal"]
    difference_points: float
    analysis_text: str


def _build_analysis_text(
    comparison: str,
    price_change: float,
    inflation: float,
    difference: float,
) -> str:
    if comparison == "equal":
        return "El precio siguió a la inflación del período."
    if comparison == "above":
        if inflation > 0:
            ratio = price_change / inflation
            return f"El producto subió {ratio:.1f}x más que la inflación del período."
        return f"El producto subió {price_change:.1f}% mientras la inflación fue 0%."
    return f"El producto subió menos que la inflación ({abs(difference):.1f} p.p. por debajo)."


_MIN_COVERAGE_RATIO = 0.7


def _compute_price_changes(db: Session, days: int) -> list[tuple[float, str]]:
    """
    Para cada (producto, supermercado) con precio registrado en al menos el
    70% de los días de la ventana de `days` días, calcula su variación de
    precio (primer precio vs. último precio dentro de la ventana). Se
    agrupa por (producto, supermercado) y no solo por producto: un mismo
    producto vendido en dos supermercados tiene dos series de precio
    independientes, y mezclarlas mediría la diferencia de precio ENTRE
    negocios en vez de el cambio de precio EN EL TIEMPO. Pares con poca
    continuidad (recién agregados, scrapeados de forma intermitente) quedan
    afuera para no meter ruido en el promedio.

    Returns:
        Lista de (change_pct, category_value) — change_pct es una fracción
        (0.02 = 2%), no un porcentaje ya multiplicado por 100. Sin orden
        garantizado; los llamadores solo necesitan iterar los valores.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    min_days = math.ceil(days * _MIN_COVERAGE_RATIO)

    rows = (
        db.query(
            PriceHistory.product_id,
            PriceHistory.supermarket,
            PriceHistory.price,
            PriceHistory.scraped_at,
            Product.category,
        )
        .join(Product, Product.id == PriceHistory.product_id)
        .filter(PriceHistory.scraped_at >= cutoff)
        .order_by(PriceHistory.product_id, PriceHistory.supermarket, PriceHistory.scraped_at.asc())
        .all()
    )

    by_pair: dict[tuple[UUID, str], list[tuple[datetime, float, str]]] = defaultdict(list)
    for product_id, supermarket, price, scraped_at, category in rows:
        by_pair[(product_id, supermarket)].append((scraped_at, float(price), category.value))

    changes: list[tuple[float, str]] = []
    for points in by_pair.values():
        distinct_days = {ts.date() for ts, _, _ in points}
        if len(distinct_days) < min_days:
            continue
        first_price = points[0][1]
        last_price = points[-1][1]
        if first_price == 0:
            continue
        category_value = points[0][2]
        changes.append(((last_price - first_price) / first_price, category_value))

    return changes


def _compute_product_price_changes(db: Session, days: int) -> list[tuple[UUID, str, float]]:
    """
    Igual que `_compute_price_changes` pero conserva `product_id` en vez de
    categoría — para "top movers" (mayor variación de precio por producto),
    no un agregado. Devuelve (product_id, supermarket, change_pct).
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    min_days = math.ceil(days * _MIN_COVERAGE_RATIO)

    rows = (
        db.query(
            PriceHistory.product_id,
            PriceHistory.supermarket,
            PriceHistory.price,
            PriceHistory.scraped_at,
        )
        .filter(PriceHistory.scraped_at >= cutoff)
        .order_by(PriceHistory.product_id, PriceHistory.supermarket, PriceHistory.scraped_at.asc())
        .all()
    )

    by_pair: dict[tuple[UUID, str], list[tuple[datetime, float]]] = defaultdict(list)
    for product_id, supermarket, price, scraped_at in rows:
        by_pair[(product_id, supermarket.value)].append((scraped_at, float(price)))

    changes: list[tuple[UUID, str, float]] = []
    for (product_id, supermarket), points in by_pair.items():
        distinct_days = {ts.date() for ts, _ in points}
        if len(distinct_days) < min_days:
            continue
        first_price = points[0][1]
        last_price = points[-1][1]
        if first_price == 0:
            continue
        changes.append((product_id, supermarket, (last_price - first_price) / first_price))

    return changes


class TopMover(BaseModel):
    product_id: UUID
    product_name: str
    change_pct: float


@router.get("/top-movers", response_model=list[TopMover])
def top_movers(
    days: int = Query(7, ge=1, le=365, description="Ventana en días"),
    limit: int = Query(6, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Productos con mayor variación de precio (en valor absoluto) en la
    ventana, con historial continuo suficiente. Reemplaza el TRENDING
    hardcodeado del home. Si un producto varió en más de un supermercado,
    se usa la variación de mayor magnitud.
    """
    changes = _compute_product_price_changes(db, days)
    if not changes:
        return []

    best_per_product: dict[UUID, float] = {}
    for product_id, _supermarket, change in changes:
        current = best_per_product.get(product_id)
        if current is None or abs(change) > abs(current):
            best_per_product[product_id] = change

    top_ids = sorted(best_per_product, key=lambda pid: abs(best_per_product[pid]), reverse=True)[:limit]
    if not top_ids:
        return []

    products = db.query(Product.id, Product.name).filter(Product.id.in_(top_ids)).all()
    name_by_id = {pid: name for pid, name in products}

    return [
        TopMover(product_id=pid, product_name=name_by_id.get(pid, ""), change_pct=round(best_per_product[pid], 4))
        for pid in top_ids
        if pid in name_by_id
    ]


class PriceIndexResponse(BaseModel):
    avg_change_pct: float | None
    basket_size: int
    period_days: int


@router.get("/price-index", response_model=PriceIndexResponse)
def price_index(
    days: int = Query(7, ge=1, le=365, description="Ventana en días"),
    db: Session = Depends(get_db),
):
    """
    Variación de precio promedio (no ponderada) de la canasta de productos
    con historial continuo suficiente en la ventana. Reemplaza el "Índice A
    Cuanto Está" hardcodeado del home.
    """
    changes = _compute_price_changes(db, days)
    if not changes:
        return PriceIndexResponse(avg_change_pct=None, basket_size=0, period_days=days)
    avg = sum(change for change, _ in changes) / len(changes)
    return PriceIndexResponse(
        avg_change_pct=round(avg, 4), basket_size=len(changes), period_days=days
    )


@router.get("/category-variation")
def category_variation(
    days: int = Query(30, ge=1, le=365, description="Ventana en días"),
    db: Session = Depends(get_db),
) -> dict[str, float]:
    """
    Variación de precio promedio por categoría, para productos con
    historial continuo suficiente en la ventana. Categorías sin canasta
    suficiente quedan ausentes del diccionario en vez de aparecer en 0%
    (que implicaría "no varió" en vez de "sin datos suficientes").
    Reemplaza CATEGORIES_VARIATION hardcodeado del dashboard de economía.
    """
    changes = _compute_price_changes(db, days)
    by_category: dict[str, list[float]] = defaultdict(list)
    for change, category_value in changes:
        by_category[category_value].append(change)
    return {
        category: round(sum(vals) / len(vals), 4)
        for category, vals in by_category.items()
    }


@router.get("/price-vs-inflation", response_model=PriceInflationAnalysis)
def price_vs_inflation(
    product_id: UUID = Query(..., description="ID del producto"),
    supermarket: Supermarket = Query(..., description="Supermercado"),
    days: int = Query(30, ge=1, le=365, description="Período en días"),
    db: Session = Depends(get_db),
):
    """
    Compara la variación de precio de un producto contra la inflación acumulada
    en el mismo período.

    Requiere al menos 2 registros de precio para el producto/supermercado en el período.
    La inflación acumulada se calcula componiendo los registros mensuales del INDEC.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    cutoff = datetime.utcnow() - timedelta(days=days)
    records = (
        db.query(PriceHistory)
        .filter(
            PriceHistory.product_id == product_id,
            PriceHistory.supermarket == supermarket,
            PriceHistory.scraped_at >= cutoff,
        )
        .order_by(PriceHistory.scraped_at.asc())
        .all()
    )

    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No hay precios de {supermarket.value} para este producto en los últimos {days} días",
        )
    if len(records) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Se necesitan al menos 2 registros de precio para comparar (encontrado: 1)",
        )

    price_start = float(records[0].price)
    price_end = float(records[-1].price)
    price_change = round(((price_end - price_start) / price_start) * 100, 2)

    # Inflación acumulada: componer los últimos N meses de inflación mensual
    months_in_period = max(1, math.ceil(days / 30))
    inflation_records = (
        db.query(EconomicIndicator)
        .filter(EconomicIndicator.indicator_type == IndicatorType.INFLATION_MONTHLY)
        .order_by(EconomicIndicator.date.desc())
        .limit(months_in_period)
        .all()
    )

    accumulated = 1.0
    for rec in inflation_records:
        accumulated *= 1 + float(rec.value) / 100
    inflation_period_pct = round((accumulated - 1) * 100, 2) if inflation_records else 0.0

    difference = round(price_change - inflation_period_pct, 2)
    if abs(difference) < 0.5:
        comparison = "equal"
    elif price_change > inflation_period_pct:
        comparison = "above"
    else:
        comparison = "below"

    return PriceInflationAnalysis(
        product_name=product.name,
        supermarket=supermarket,
        period_days=days,
        price_start=price_start,
        price_end=price_end,
        price_change_percent=price_change,
        inflation_period_percent=inflation_period_pct,
        comparison=comparison,
        difference_points=difference,
        analysis_text=_build_analysis_text(comparison, price_change, inflation_period_pct, difference),
    )


class DiscountCheck(BaseModel):
    has_active_sale: bool
    claimed_original_price: float | None = None
    claimed_discount_percent: float | None = None
    real_recent_max_price: float | None = None
    real_discount_percent: float | None = None
    is_suspicious: bool = False
    reason: str


_DISCOUNT_LOOKBACK_DAYS = 45
_DISCOUNT_TOLERANCE_PCT = 5.0


@router.get("/discount-check", response_model=DiscountCheck)
def discount_check(
    product_id: UUID = Query(..., description="ID del producto"),
    supermarket: Supermarket = Query(..., description="Supermercado"),
    db: Session = Depends(get_db),
):
    """
    Verifica si el "precio de lista" detrás de una oferta activa es real:
    compara contra el precio más alto REALMENTE cobrado en los últimos
    `_DISCOUNT_LOOKBACK_DAYS` días. Si el precio de lista declarado supera
    ese máximo real (con un margen de tolerancia), el descuento probablemente
    infla el precio "antes" para simular un ahorro que no es tal ("oferta falsa"
    / "precio ancla" inflado) — un patrón conocido en e-commerce de supermercados.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    current = (
        db.query(PriceHistory)
        .filter(
            PriceHistory.product_id == product_id,
            PriceHistory.supermarket == supermarket,
        )
        .order_by(PriceHistory.scraped_at.desc())
        .first()
    )
    if not current:
        raise HTTPException(
            status_code=404,
            detail=f"No hay precios de {supermarket.value} para este producto",
        )

    if not current.was_on_sale or not current.original_price:
        return DiscountCheck(has_active_sale=False, reason="Este precio no está marcado como oferta.")

    cutoff = datetime.utcnow() - timedelta(days=_DISCOUNT_LOOKBACK_DAYS)
    recent = (
        db.query(PriceHistory.price)
        .filter(
            PriceHistory.product_id == product_id,
            PriceHistory.supermarket == supermarket,
            PriceHistory.scraped_at >= cutoff,
            PriceHistory.id != current.id,
        )
        .all()
    )
    if not recent:
        return DiscountCheck(
            has_active_sale=True,
            claimed_original_price=float(current.original_price),
            claimed_discount_percent=float(current.discount_percentage) if current.discount_percentage else None,
            reason="No hay suficiente historial reciente para verificar el precio de lista.",
        )

    real_max = max(float(p[0]) for p in recent)
    claimed_original = float(current.original_price)
    current_price = float(current.price)
    real_discount_pct = round((1 - current_price / real_max) * 100, 2) if real_max else None
    is_suspicious = claimed_original > real_max * (1 + _DISCOUNT_TOLERANCE_PCT / 100)

    reason = (
        f"El precio de lista (${claimed_original:.0f}) es más alto que cualquier precio real "
        f"registrado en los últimos {_DISCOUNT_LOOKBACK_DAYS} días (máximo real: ${real_max:.0f})."
        if is_suspicious
        else "El precio de lista coincide con el historial real reciente."
    )

    return DiscountCheck(
        has_active_sale=True,
        claimed_original_price=claimed_original,
        claimed_discount_percent=float(current.discount_percentage) if current.discount_percentage else None,
        real_recent_max_price=real_max,
        real_discount_percent=real_discount_pct,
        is_suspicious=is_suspicious,
        reason=reason,
    )
