"""
Router principal de la API v1.
Agrupa todos los routers de endpoints.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import analysis, economic, locations, prices, products, supermarkets

api_router = APIRouter()
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(prices.router, tags=["prices"])
api_router.include_router(economic.router, prefix="/economic", tags=["economic"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(supermarkets.router, tags=["supermarkets"])
