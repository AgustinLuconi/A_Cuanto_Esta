"""
Endpoints de datos oficiales del INDEC (leen de la base propia).

GET /api/v1/indec/series   — Series filtradas por dataset/código/región/indicador
GET /api/v1/indec/overview — Último valor de las series de la pantalla de economía
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.indec import IndecOverview, ObservationOut
from app.services.indec import queries

router = APIRouter()


@router.get("/series", response_model=list[ObservationOut])
def get_indec_series(
    dataset: str = Query(..., description="Slug del dataset, ej. ipc_nacional"),
    code: str | None = Query(None, description="Código de serie, ej. 01"),
    region: str | None = Query(None, description="Ej. Nacional, GBA"),
    indicator: str | None = Query(None, description="Ej. Indice, v_m, v_ia"),
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
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/overview", response_model=IndecOverview)
def get_indec_overview(db: Session = Depends(get_db)):
    return queries.get_overview(db)
