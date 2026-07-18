import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.config.database import Base


class MatchType(str, enum.Enum):
    BARCODE = "BARCODE"
    FUZZY   = "FUZZY"
    MANUAL  = "MANUAL"


class ProductAlias(Base):
    __tablename__ = "product_aliases"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alias_source         = Column(String(50),  nullable=False, index=True)   # ej: "la_anonima"
    alias_id             = Column(String(100), nullable=False, index=True)   # ej: "la_anonima_2105214"
    canonical_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    match_type           = Column(SQLEnum(MatchType), nullable=False)
    confidence           = Column(Float, nullable=False, default=1.0)
    created_at           = Column(DateTime, default=datetime.utcnow, nullable=False)

    canonical_product = relationship("Product")

    __table_args__ = (
        UniqueConstraint("alias_source", "alias_id", name="uq_alias_source_id"),
    )
