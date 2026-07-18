"""
Endpoint de supermercados: logos y metadatos.
"""
from fastapi import APIRouter, Request
from app.models.price_history import Supermarket

router = APIRouter()


@router.get("/supermarkets/logos")
def get_supermarket_logos(request: Request):
    """
    Devuelve URLs absolutas de los logos de cada supermercado.
    Los archivos PNG están en /static/logos/{nombre}.png
    """
    base = str(request.base_url).rstrip("/")
    return {s.value: f"{base}/static/logos/{s.value}.png" for s in Supermarket}
