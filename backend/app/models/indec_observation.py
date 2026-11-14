"""
Modelo de observaciones de la API del INDEC (https://api.indec.gob.ar).

Formato largo: una fila por (dataset, serie, región, tipo de indicador, período).
Es independiente de `economic_indicators`, que no tiene lugar para región,
nivel ni tipo de indicador.
"""
import uuid

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.config.database import Base
from app.utils.time import utcnow_aware


class IndecObservation(Base):
    """Un valor publicado por el INDEC para una serie en un período."""

    __tablename__ = "indec_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Origen y serie
    dataset = Column(String(80), nullable=False)          # slug, ej. "ipc_nacional"
    classifier = Column(String(120), nullable=False)      # ej. "COICOP Argentina 2019"
    level = Column(String(60), nullable=False)            # ej. "División", "Producto"
    series_code = Column(String(40), nullable=False)      # ej. "01", "CBA"
    series_name = Column(Text, nullable=False)            # descripción legible (texto libre del INDEC)

    # NOT NULL a propósito: en PostgreSQL dos NULL no cuentan como iguales en
    # una restricción única y el upsert duplicaría filas. Los datasets sin
    # región (ej. indice_salarios) se guardan como "Nacional".
    region = Column(String(40), nullable=False)

    indicator_type = Column(String(60), nullable=False)   # ej. "Indice", "v_m", "v_ia"
    unit = Column(Text)                                   # ej. "Porcentaje" (texto libre del INDEC)

    # Dato
    period = Column(Date, nullable=False)                 # primer día del mes
    value = Column(Numeric(18, 4), nullable=False)
    notes = Column(Text)

    ingested_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow_aware
    )

    __table_args__ = (
        UniqueConstraint(
            "dataset",
            "classifier",
            "level",
            "series_code",
            "region",
            "indicator_type",
            "period",
            name="uq_indec_observation_key",
        ),
        Index(
            "ix_indec_observation_lookup",
            "dataset",
            "series_code",
            "region",
            "indicator_type",
            "period",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<IndecObservation {self.dataset}/{self.series_code}/"
            f"{self.region}/{self.indicator_type} {self.period}={self.value}>"
        )
