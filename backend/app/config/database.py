"""
Configuración de SQLAlchemy y sesión de base de datos
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config.settings import settings

# Crear engine de SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,  # Verifica conexión antes de usar
    pool_size=10,  # Tamaño del pool de conexiones
    max_overflow=20  # Conexiones adicionales permitidas
)

# SessionLocal para crear sesiones de BD
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para modelos declarativos
Base = declarative_base()


def get_db():
    """
    Dependency para obtener sesión de base de datos.
    Uso en FastAPI:
        @app.get("/")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializar base de datos (crear todas las tablas).
    Usar solo en desarrollo. En producción usar Alembic.
    """
    Base.metadata.create_all(bind=engine)
