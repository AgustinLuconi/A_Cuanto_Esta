"""
Modelo de base de datos para Indicadores Económicos
"""
from sqlalchemy import Column, String, Numeric, DateTime, Date, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, date
import uuid
import enum

from app.config.database import Base


class IndicatorType(str, enum.Enum):
    """Tipos de indicadores económicos"""
    INFLATION_MONTHLY = "inflation_monthly"  # Inflación mensual
    INFLATION_YEARLY = "inflation_yearly"    # Inflación interanual
    DOLLAR_BLUE = "dollar_blue"              # Dólar blue
    DOLLAR_OFICIAL = "dollar_oficial"        # Dólar oficial
    DOLLAR_MEP = "dollar_mep"                # Dólar MEP
    DOLLAR_CCL = "dollar_ccl"                # Dólar CCL
    UVA_INDEX = "uva_index"                  # Índice UVA
    PLAZO_FIJO_RATE = "plazo_fijo_rate"      # Tasa plazo fijo
    RISK_COUNTRY = "risk_country"            # Riesgo país
    IPC_CATEGORY = "ipc_category"            # IPC por categoría


class DataSource(str, enum.Enum):
    """Fuentes de datos"""
    ARGENTINADATOS = "argentinadatos"
    DOLARAPI = "dolarapi"
    DATOS_GOB_AR = "datos_gob_ar"
    BCRA = "bcra"
    INDEC = "indec"


class EconomicIndicator(Base):
    """
    Modelo de Indicadores Económicos.
    Almacena datos macroeconómicos históricos.
    """
    __tablename__ = "economic_indicators"
    
    # Identificador
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tipo de indicador
    indicator_type = Column(SQLEnum(IndicatorType), nullable=False, index=True)
    
    # Valor del indicador
    value = Column(Numeric(12, 4), nullable=False)
    
    # Categoría (para IPC por categoría, etc.)
    category = Column(String(100))  # Ej: "alimentos", "transporte"
    
    # Fecha del dato
    date = Column(Date, nullable=False, index=True)
    
    # Fuente del dato
    source = Column(SQLEnum(DataSource), nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Información adicional en JSON (opcional)
    metadata_json = Column(String(1000))  # Para datos extra como notas, etc.
    
    # Índices compuestos
    __table_args__ = (
        Index('idx_indicator_date', 'indicator_type', 'date'),
        Index('idx_indicator_category_date', 'indicator_type', 'category', 'date'),
    )
    
    def __repr__(self):
        return f"<EconomicIndicator(type={self.indicator_type.value}, value={self.value}, date={self.date})>"
    
    @classmethod
    def get_latest_value(cls, session, indicator_type: IndicatorType, category: str = None):
        """
        Obtener el valor más reciente de un indicador.
        
        Args:
            session: Sesión de SQLAlchemy
            indicator_type: Tipo de indicador
            category: Categoría opcional (para IPC)
        
        Returns:
            EconomicIndicator o None
        """
        query = session.query(cls).filter(
            cls.indicator_type == indicator_type
        )
        
        if category:
            query = query.filter(cls.category == category)
        
        return query.order_by(cls.date.desc()).first()
