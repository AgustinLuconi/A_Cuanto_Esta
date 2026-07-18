"""
Endpoints de Ubicaciones Geográficas.

GET /api/v1/locations/regions           — Listar regiones con provincias
GET /api/v1/locations/provinces         — Listar provincias
GET /api/v1/locations/coverage          — Cobertura de datos por ubicación
GET /api/v1/locations/prices/by-location — Precios filtrados por ubicación
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.location import Province, Region, REGION_PROVINCES
from app.models.price_history import PriceHistory, Supermarket
from app.models.product import Product
from app.utils.location_utils import (
    get_province_display_name,
    get_region_display_name,
    get_region_from_province,
)

router = APIRouter()


@router.get("/regions")
def list_regions():
    """Lista todas las regiones de Argentina con sus provincias."""
    return {
        "regions": [
            {
                "code": r.value,
                "name": get_region_display_name(r.value),
                "provinces": [
                    {"code": p.value, "name": get_province_display_name(p.value)}
                    for p in REGION_PROVINCES.get(r, [])
                ],
            }
            for r in Region
        ]
    }


@router.get("/provinces")
def list_provinces():
    """Lista todas las provincias de Argentina con su región primaria."""
    return {
        "provinces": [
            {
                "code": p.value,
                "name": get_province_display_name(p.value),
                "region": get_region_from_province(p.value),
            }
            for p in Province
        ]
    }


@router.get("/coverage")
def get_coverage(db: Session = Depends(get_db)):
    """Muestra qué regiones y provincias tienen datos de precios en la BD."""
    regions_with_data = [
        r[0]
        for r in db.query(distinct(PriceHistory.region))
        .filter(PriceHistory.region.isnot(None))
        .all()
        if r[0]
    ]

    provinces_with_data = [
        p[0]
        for p in db.query(distinct(PriceHistory.province))
        .filter(PriceHistory.province.isnot(None))
        .all()
        if p[0]
    ]

    supermarkets_by_region = {}
    for region in regions_with_data:
        supers = (
            db.query(distinct(PriceHistory.supermarket))
            .filter(PriceHistory.region == region)
            .all()
        )
        supermarkets_by_region[region] = [s[0].value for s in supers]

    total_records = db.query(func.count(PriceHistory.id)).scalar()
    with_location = (
        db.query(func.count(PriceHistory.id))
        .filter(PriceHistory.region.isnot(None))
        .scalar()
    )

    return {
        "regions_with_data": [
            {"code": r, "name": get_region_display_name(r)} for r in regions_with_data
        ],
        "provinces_with_data": [
            {"code": p, "name": get_province_display_name(p)}
            for p in provinces_with_data
        ],
        "supermarkets_by_region": supermarkets_by_region,
        "stats": {
            "total_records": total_records,
            "records_with_location": with_location,
            "coverage_percentage": (
                round(with_location / total_records * 100, 2)
                if total_records
                else 0
            ),
        },
    }


@router.get("/prices/by-location")
def get_prices_by_location(
    product_id: UUID,
    region: str | None = Query(None, description="Filtrar por región (ej: cuyo, amba)"),
    province: str | None = Query(None, description="Filtrar por provincia (ej: mendoza)"),
    supermarket: Supermarket | None = Query(None, description="Filtrar por supermercado"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Precios de un producto filtrados por ubicación geográfica."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    query = db.query(PriceHistory).filter(PriceHistory.product_id == product_id)
    if region:
        query = query.filter(PriceHistory.region == region.lower())
    if province:
        query = query.filter(PriceHistory.province == province.lower())
    if supermarket:
        query = query.filter(PriceHistory.supermarket == supermarket)

    prices = query.order_by(PriceHistory.scraped_at.desc()).limit(limit).all()

    return {
        "product": {
            "id": str(product.id),
            "name": product.name,
            "brand": product.brand,
        },
        "filters": {
            "region": region,
            "province": province,
            "supermarket": supermarket.value if supermarket else None,
        },
        "count": len(prices),
        "prices": [
            {
                "supermarket": p.supermarket.value,
                "price": float(p.price),
                "was_on_sale": p.was_on_sale,
                "province": p.province,
                "region": p.region,
                "city": p.city,
                "scraped_at": p.scraped_at.isoformat(),
            }
            for p in prices
        ],
    }
