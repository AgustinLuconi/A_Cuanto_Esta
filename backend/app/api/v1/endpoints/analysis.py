"""
Endpoints de Análisis.

GET /api/v1/analysis/price-vs-inflation — Comparar evolución de precio contra inflación
"""
import math
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
