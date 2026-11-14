"""
Endpoints de datos oficiales del INDEC (leen de la base propia).

GET /api/v1/indec/series   — Series filtradas por dataset/código/región/indicador
GET /api/v1/indec/overview — Último valor de las series de la pantalla de economía
GET /api/v1/indec/price-reference — Precios promedio del INDEC vs. nuestros supermercados
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.indec import IndecOverview, ObservationOut, PriceReferenceItemOut
from app.services.indec import price_reference_queries, queries

router = APIRouter()


@router.get("/series", response_model=list[ObservationOut])
def get_indec_series(
    dataset: str = Query(..., description="Slug del dataset, ej. ipc_nacional"),
    code: str | None = Query(None, description="Código de serie, ej. 01"),
    region: str | None = Query(None, description="Ej. Nacional, GBA"),
    indicator: str | None = Query(None, description="Ej. Indice, v_m, v_ia"),
    classifier: str | None = Query(None, description="Ej. IPC, COICOP Argentina 2019"),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    return queries.get_series(
        db,
        dataset=dataset,
        code=code,
        region=region,
        indicator=indicator,
        classifier=classifier,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/overview", response_model=IndecOverview)
def get_indec_overview(db: Session = Depends(get_db)):
    return queries.get_overview(db)


@router.get("/price-reference", response_model=list[PriceReferenceItemOut])
def get_indec_price_reference(db: Session = Depends(get_db)):
    """
    Precio promedio oficial del INDEC (GBA) contra la mediana de los productos
    equivalentes de nuestros supermercados, por artículo. Solo incluye los artículos
    con suficientes ofertas frescas; con datos insuficientes devuelve una lista vacía.
    """
    return price_reference_queries.get_price_reference(db)
