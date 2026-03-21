"""
Endpoints de Precios.

GET /api/v1/products/{product_id}/prices/history  — Historial de precios
GET /api/v1/prices/compare                         — Comparar entre supermercados
GET /api/v1/prices/current                         — Snapshot de precios actuales
"""
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.price_history import PriceHistory, Supermarket
from app.models.product import Product, ProductCategory
from app.schemas import price as schemas_price

router = APIRouter()


def _get_current_prices(db: Session, product_id: UUID) -> list[PriceHistory]:
    """Devuelve el registro de precio más reciente por supermercado para un producto."""
    latest = (
        db.query(
            PriceHistory.supermarket,
            func.max(PriceHistory.scraped_at).label("max_at"),
        )
        .filter(PriceHistory.product_id == product_id)
        .group_by(PriceHistory.supermarket)
        .subquery()
    )
    return (
        db.query(PriceHistory)
        .join(
            latest,
            and_(
                PriceHistory.supermarket == latest.c.supermarket,
                PriceHistory.scraped_at == latest.c.max_at,
                PriceHistory.product_id == product_id,
            ),
        )
        .all()
    )


@router.get(
    "/products/{product_id}/prices/history",
    response_model=list[schemas_price.PriceHistory],
)
def get_price_history(
    product_id: UUID,
    supermarket: Supermarket | None = None,
    days: int = Query(30, ge=0, description="Últimos N días. 0 = sin límite."),
    db: Session = Depends(get_db),
):
    """
    Historial de precios de un producto.

    Ordenado por fecha descendente. Filtrable por supermercado y rango de días.
    `days=0` devuelve todo el historial disponible.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    query = db.query(PriceHistory).filter(PriceHistory.product_id == product_id)

    if supermarket:
        query = query.filter(PriceHistory.supermarket == supermarket)
    if days > 0:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.filter(PriceHistory.scraped_at >= cutoff)

    records = query.order_by(PriceHistory.scraped_at.desc()).all()
    if not records:
        raise HTTPException(
            status_code=404, detail="No hay registros de precios para este producto"
        )
    return records


@router.get("/prices/compare", response_model=schemas_price.PriceComparison)
def compare_prices(
    product_id: UUID = Query(..., description="ID del producto a comparar"),
    db: Session = Depends(get_db),
):
    """
    Comparar el precio actual de un producto entre supermercados.

    Devuelve el precio vigente por supermercado junto con el mejor precio,
    el más alto y la diferencia porcentual entre ambos.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    current_prices = _get_current_prices(db, product_id)
    if not current_prices:
        raise HTTPException(
            status_code=404, detail="No hay precios disponibles para este producto"
        )

    price_values = [float(ph.price) for ph in current_prices]
    lowest = min(price_values)
    highest = max(price_values)
    difference = round(highest - lowest, 2)
    difference_pct = round((difference / highest) * 100, 2) if highest else 0.0
    best_deal = min(current_prices, key=lambda ph: float(ph.price)).supermarket

    return schemas_price.PriceComparison(
        product_id=product.id,
        product_name=product.name,
        prices=[
            schemas_price.CurrentPrice(
                supermarket=ph.supermarket,
                price=ph.price,
                was_on_sale=ph.was_on_sale,
                original_price=ph.original_price,
                discount_percentage=ph.discount_percentage,
                url=ph.url,
                last_updated=ph.scraped_at,
                in_stock=ph.in_stock,
            )
            for ph in current_prices
        ],
        lowest_price=lowest,
        highest_price=highest,
        price_difference=difference,
        price_difference_percentage=difference_pct,
        best_deal=best_deal,
    )


@router.get("/prices/current", response_model=list[schemas_price.CurrentPrice])
def get_current_prices(
    supermarket: Supermarket | None = None,
    category: ProductCategory | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Snapshot de precios actuales (el registro más reciente por producto y supermercado).

    Filtrable por supermercado y categoría de producto.
    """
    latest_sq = (
        db.query(
            PriceHistory.product_id,
            PriceHistory.supermarket,
            func.max(PriceHistory.scraped_at).label("max_at"),
        )
        .group_by(PriceHistory.product_id, PriceHistory.supermarket)
        .subquery()
    )

    query = db.query(PriceHistory).join(
        latest_sq,
        and_(
            PriceHistory.product_id == latest_sq.c.product_id,
            PriceHistory.supermarket == latest_sq.c.supermarket,
            PriceHistory.scraped_at == latest_sq.c.max_at,
        ),
    )

    if supermarket:
        query = query.filter(PriceHistory.supermarket == supermarket)
    if category:
        query = query.join(Product, PriceHistory.product_id == Product.id).filter(
            Product.category == category
        )

    records = query.order_by(PriceHistory.scraped_at.desc()).offset(skip).limit(limit).all()

    return [
        schemas_price.CurrentPrice(
            supermarket=ph.supermarket,
            price=ph.price,
            was_on_sale=ph.was_on_sale,
            original_price=ph.original_price,
            discount_percentage=ph.discount_percentage,
            url=ph.url,
            last_updated=ph.scraped_at,
            in_stock=ph.in_stock,
        )
        for ph in records
    ]
