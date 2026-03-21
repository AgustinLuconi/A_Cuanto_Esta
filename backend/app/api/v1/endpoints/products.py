"""
Endpoints de Productos.

GET /api/v1/products          — Listado con paginación y filtros
GET /api/v1/products/search   — Búsqueda avanzada con filtros de precio
GET /api/v1/products/{id}     — Detalle con precios actuales por supermercado
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.price_history import PriceHistory
from app.models.product import Product, ProductCategory
from app.schemas import price as price_schemas
from app.schemas import product as product_schemas

router = APIRouter()


def _get_current_prices(db: Session, product_id: UUID) -> list[PriceHistory]:
    """
    Devuelve el registro de precio más reciente por supermercado para un producto.
    Usa subquery 'latest row per group' para eficiencia.
    """
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


@router.get("/search", response_model=list[product_schemas.Product])
def search_products(
    q: str = Query(..., min_length=1, description="Texto a buscar en nombre del producto"),
    category: ProductCategory | None = None,
    brand: str | None = None,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Búsqueda avanzada de productos.

    Soporta filtros por texto, categoría, marca y rango de precios.
    El filtro de precios aplica sobre el precio más reciente registrado.
    """
    query = db.query(Product).filter(
        Product.normalized_name.ilike(f"%{q.lower()}%")
    )

    if category:
        query = query.filter(Product.category == category)
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))

    if min_price is not None or max_price is not None:
        # Subquery: precio más reciente por producto
        latest_price_sq = (
            db.query(
                PriceHistory.product_id,
                func.max(PriceHistory.scraped_at).label("max_at"),
            )
            .group_by(PriceHistory.product_id)
            .subquery()
        )
        latest_ph = (
            db.query(PriceHistory.product_id, PriceHistory.price)
            .join(
                latest_price_sq,
                and_(
                    PriceHistory.product_id == latest_price_sq.c.product_id,
                    PriceHistory.scraped_at == latest_price_sq.c.max_at,
                ),
            )
            .subquery()
        )
        query = query.join(latest_ph, Product.id == latest_ph.c.product_id)
        if min_price is not None:
            query = query.filter(latest_ph.c.price >= min_price)
        if max_price is not None:
            query = query.filter(latest_ph.c.price <= max_price)

    return query.offset(skip).limit(limit).all()


@router.get("", response_model=list[product_schemas.Product])
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category: ProductCategory | None = None,
    search: str | None = Query(None, min_length=1),
    db: Session = Depends(get_db),
):
    """
    Listar productos con paginación y filtros opcionales.

    - **category**: filtrar por categoría (lacteos, bebidas, limpieza, etc.)
    - **search**: buscar por nombre normalizado (insensible a mayúsculas)
    """
    query = db.query(Product)

    if category:
        query = query.filter(Product.category == category)
    if search:
        query = query.filter(Product.normalized_name.ilike(f"%{search.lower()}%"))

    return query.order_by(Product.name).offset(skip).limit(limit).all()


@router.get("/{product_id}", response_model=product_schemas.ProductWithPrices)
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    """
    Detalle de un producto con precios actuales en todos los supermercados.

    Incluye el precio más bajo, más alto y la diferencia entre supermercados.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    current_prices = _get_current_prices(db, product_id)
    prices_values = [float(ph.price) for ph in current_prices]

    lowest = min(prices_values) if prices_values else None
    highest = max(prices_values) if prices_values else None
    difference = round(highest - lowest, 2) if (highest and lowest) else None

    return product_schemas.ProductWithPrices(
        **product_schemas.Product.model_validate(product).model_dump(),
        current_prices=[
            price_schemas.CurrentPrice(
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
    )
