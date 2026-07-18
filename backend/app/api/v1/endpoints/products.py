"""
Endpoints de Productos.

GET /api/v1/products          — Listado con paginación y filtros
GET /api/v1/products/search   — Búsqueda avanzada con filtros de precio y variación
GET /api/v1/products/{id}     — Detalle con precios actuales por supermercado
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.price_history import PriceHistory
from app.models.product import Product, ProductCategory
from app.schemas import price as price_schemas
from app.schemas import product as product_schemas

router = APIRouter()


class SortOrder(str, Enum):
    RELEVANCE = "relevance"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    VARIATION = "variation"  # spread porcentual entre supermercados


def _min_price_subquery(db: Session):
    """Subquery: precio mínimo actual por producto (mínimo entre todos los supermercados)."""
    latest_sq = (
        db.query(
            PriceHistory.product_id,
            PriceHistory.supermarket,
            func.max(PriceHistory.scraped_at).label("max_at"),
        )
        .group_by(PriceHistory.product_id, PriceHistory.supermarket)
        .subquery()
    )
    return (
        db.query(
            PriceHistory.product_id,
            func.min(PriceHistory.price).label("min_price"),
        )
        .join(
            latest_sq,
            and_(
                PriceHistory.product_id == latest_sq.c.product_id,
                PriceHistory.supermarket == latest_sq.c.supermarket,
                PriceHistory.scraped_at == latest_sq.c.max_at,
            ),
        )
        .group_by(PriceHistory.product_id)
        .subquery()
    )


def _apply_price_sort(query, min_price_sq, sort: SortOrder):
    """Agrega OUTERJOIN con min_price_sq y aplica el ORDER BY correspondiente."""
    query = query.outerjoin(min_price_sq, Product.id == min_price_sq.c.product_id)
    col = min_price_sq.c.min_price
    if sort == SortOrder.PRICE_ASC:
        return query.order_by(col.asc().nullslast())
    return query.order_by(col.desc().nullslast())


def _price_spread_subquery(db: Session):
    """Spread porcentual (max-min)/min × 100 entre supermercados actuales por producto."""
    latest_sq = (
        db.query(
            PriceHistory.product_id,
            PriceHistory.supermarket,
            func.max(PriceHistory.scraped_at).label("max_at"),
        )
        .group_by(PriceHistory.product_id, PriceHistory.supermarket)
        .subquery()
    )
    return (
        db.query(
            PriceHistory.product_id,
            (
                (func.max(PriceHistory.price) - func.min(PriceHistory.price))
                / func.nullif(func.min(PriceHistory.price), 0)
                * 100
            ).label("spread"),
        )
        .join(
            latest_sq,
            and_(
                PriceHistory.product_id == latest_sq.c.product_id,
                PriceHistory.supermarket == latest_sq.c.supermarket,
                PriceHistory.scraped_at == latest_sq.c.max_at,
            ),
        )
        .group_by(PriceHistory.product_id)
        .subquery()
    )


def _variation_subquery(db: Session):
    """
    Subquery: variación % de precio en 30 días por producto.

    Compara el precio mínimo actual (más reciente por supermercado) con el precio
    mínimo disponible entre 25 y 35 días atrás. Solo incluye productos con datos
    en ambas ventanas temporales.
    """
    # Precio actual: mínimo entre supermercados del precio más reciente por (product, sm)
    latest_sm_sq = (
        db.query(
            PriceHistory.product_id,
            PriceHistory.supermarket,
            func.max(PriceHistory.scraped_at).label("max_at"),
        )
        .group_by(PriceHistory.product_id, PriceHistory.supermarket)
        .subquery()
    )
    recent_sq = (
        db.query(
            PriceHistory.product_id,
            func.min(PriceHistory.price).label("price_now"),
        )
        .join(
            latest_sm_sq,
            and_(
                PriceHistory.product_id == latest_sm_sq.c.product_id,
                PriceHistory.supermarket == latest_sm_sq.c.supermarket,
                PriceHistory.scraped_at == latest_sm_sq.c.max_at,
            ),
        )
        .group_by(PriceHistory.product_id)
        .subquery()
    )

    cutoff_start = datetime.utcnow() - timedelta(days=35)
    cutoff_end = datetime.utcnow() - timedelta(days=25)
    old_sq = (
        db.query(
            PriceHistory.product_id,
            func.min(PriceHistory.price).label("price_then"),
        )
        .filter(PriceHistory.scraped_at.between(cutoff_start, cutoff_end))
        .group_by(PriceHistory.product_id)
        .subquery()
    )

    return (
        db.query(
            recent_sq.c.product_id,
            (
                (recent_sq.c.price_now - old_sq.c.price_then)
                / func.nullif(old_sq.c.price_then, 0)
                * 100
            ).label("variation_pct"),
        )
        .join(old_sq, recent_sq.c.product_id == old_sq.c.product_id)
        .subquery()
    )


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


@router.get("/search", response_model=product_schemas.ProductList)
def search_products(
    q: str = Query(..., min_length=1, description="Texto a buscar en nombre del producto"),
    category: ProductCategory | None = None,
    brand: str | None = None,
    price_min: float | None = Query(None, ge=0),
    price_max: float | None = Query(None, ge=0),
    variation_filter: Literal["down", "low", "high"] | None = None,
    sort: SortOrder = SortOrder.RELEVANCE,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Product).filter(
        Product.normalized_name.ilike(f"%{q.lower()}%")
    )

    if category:
        query = query.filter(Product.category == category)
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))

    if price_min is not None or price_max is not None:
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
        if price_min is not None:
            query = query.filter(latest_ph.c.price >= price_min)
        if price_max is not None:
            query = query.filter(latest_ph.c.price <= price_max)

    # Facets calculados sobre la query base (sin variation_filter), para que los
    # counts reflejen el universo completo de la búsqueda independientemente del
    # filtro de variación activo.
    base_product_ids = query.with_entities(Product.id).subquery()

    sm_rows = (
        db.query(
            PriceHistory.supermarket,
            func.count(func.distinct(PriceHistory.product_id)).label("cnt"),
        )
        .filter(PriceHistory.product_id.in_(base_product_ids))
        .group_by(PriceHistory.supermarket)
        .all()
    )
    supermarket_counts = {row.supermarket.value: row.cnt for row in sm_rows}

    variation_sq = _variation_subquery(db)
    var_row = (
        db.query(
            func.sum(case((variation_sq.c.variation_pct < 0, 1), else_=0)).label("down"),
            func.sum(
                case(
                    (
                        and_(
                            variation_sq.c.variation_pct >= 0,
                            variation_sq.c.variation_pct <= 5,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("low"),
            func.sum(case((variation_sq.c.variation_pct > 10, 1), else_=0)).label("high"),
        )
        .filter(variation_sq.c.product_id.in_(base_product_ids))
        .one()
    )
    variation_counts = {
        "down": int(var_row.down or 0),
        "low": int(var_row.low or 0),
        "high": int(var_row.high or 0),
    }

    # Aplicar filtro de variación después de calcular los facets
    if variation_filter is not None:
        query = query.join(variation_sq, Product.id == variation_sq.c.product_id)
        if variation_filter == "down":
            query = query.filter(variation_sq.c.variation_pct < 0)
        elif variation_filter == "low":
            query = query.filter(
                variation_sq.c.variation_pct >= 0,
                variation_sq.c.variation_pct <= 5,
            )
        elif variation_filter == "high":
            query = query.filter(variation_sq.c.variation_pct > 10)

    total = query.count()

    if sort in (SortOrder.PRICE_ASC, SortOrder.PRICE_DESC):
        query = _apply_price_sort(query, _min_price_subquery(db), sort)
    elif sort == SortOrder.VARIATION:
        spread_sq = _price_spread_subquery(db)
        query = (
            query
            .outerjoin(spread_sq, Product.id == spread_sq.c.product_id)
            .order_by(spread_sq.c.spread.desc().nullslast())
        )

    items = query.offset(skip).limit(limit).all()
    return product_schemas.ProductList(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        supermarket_counts=supermarket_counts,
        variation_counts=variation_counts,
    )


@router.get("", response_model=product_schemas.ProductList)
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category: ProductCategory | None = None,
    search: str | None = Query(None, min_length=1),
    sort: SortOrder = SortOrder.RELEVANCE,
    db: Session = Depends(get_db),
):
    query = db.query(Product)

    if category:
        query = query.filter(Product.category == category)
    if search:
        query = query.filter(Product.normalized_name.ilike(f"%{search.lower()}%"))

    total = query.count()

    if sort in (SortOrder.PRICE_ASC, SortOrder.PRICE_DESC):
        query = _apply_price_sort(query, _min_price_subquery(db), sort)
    elif sort == SortOrder.VARIATION:
        spread_sq = _price_spread_subquery(db)
        query = (query
                 .outerjoin(spread_sq, Product.id == spread_sq.c.product_id)
                 .order_by(spread_sq.c.spread.desc().nullslast()))
    else:
        query = query.order_by(Product.name)

    items = query.offset(skip).limit(limit).all()
    return product_schemas.ProductList(items=items, total=total, skip=skip, limit=limit)


@router.get("/count")
def count_products(
    category: ProductCategory | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Total de productos, opcionalmente filtrado por categoría."""
    query = db.query(func.count(Product.id))
    if category:
        query = query.filter(Product.category == category)
    return {"count": query.scalar()}


@router.get("/facets")
def get_product_facets(
    q: str | None = Query(None, min_length=1),
    db: Session = Depends(get_db),
) -> dict:
    """Count de productos por categoría. Con q, filtra por texto de búsqueda."""
    base = db.query(Product.category, func.count(Product.id))
    if q:
        base = base.filter(Product.normalized_name.ilike(f"%{q.lower()}%"))
    rows = base.group_by(Product.category).all()
    result = {cat.value: 0 for cat in ProductCategory}
    for cat, count in rows:
        result[cat.value] = count
    return result


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
