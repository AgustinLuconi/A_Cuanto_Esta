"""
Aplicación principal de FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config.settings import settings

# En producción se ocultan /docs, /redoc y el schema OpenAPI para no exponer
# la superficie completa de la API sin necesidad.
_is_production = settings.ENVIRONMENT == "production"

# Crear instancia de FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API para comparación de precios de supermercados argentinos con contexto económico",
    debug=settings.DEBUG,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def root():
    """Endpoint raíz"""
    return {
        "message": "A Cuanto Está API",
        "version": settings.VERSION,
        "status": "running",
        "docs": None if _is_production else "/docs",
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


from app.api.v1.api import api_router
app.include_router(api_router, prefix="/api/v1")
