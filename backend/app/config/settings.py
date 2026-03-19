"""
Configuración de la aplicación usando Pydantic Settings.
Carga variables de entorno desde .env
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator


class Settings(BaseSettings):
    """Configuración general de la aplicación"""
    
    # Información del proyecto
    PROJECT_NAME: str = "A Cuanto Está"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Base de datos
    DATABASE_URL: str
    DATABASE_ECHO: bool = False
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Redis y Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Scraping
    SCRAPING_DELAY: int = 2
    SCRAPING_TIMEOUT: int = 30
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # APIs externas
    ARGENTINA_DATOS_API_URL: str = "https://api.argentinadatos.com"
    DOLAR_API_URL: str = "https://dolarapi.com"
    DATOS_GOB_AR_API_URL: str = "https://apis.datos.gob.ar/series/api"

    # Coto Digital (Constructor.io)
    COTO_BASE_URL: str = "https://www.cotodigital.com.ar"
    CONSTRUCTOR_API_URL: str = "https://ac.cnstrc.com"
    COTO_CONSTRUCTOR_KEY: str = "key_r6xzz4IAoTWcipni"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Cache
    CACHE_TTL: int = 3600  # 1 hora
    PRICE_CACHE_TTL: int = 1800  # 30 minutos
    
    # Scraping Schedule
    SCRAPING_SCHEDULE_HOUR: int = 2
    SCRAPING_SCHEDULE_MINUTE: int = 0
    
    # Security
    SECRET_KEY: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()
