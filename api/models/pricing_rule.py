import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Date, Integer, Enum, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base
from core.enums import PricingAdjustmentType


class PricingRule(Base):
    __tablename__ = "pricing_rules"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_pricing_rules_end_after_start"),
        CheckConstraint(
            "(adjustment_type = 'PERCENTAGE' AND adjustment_value > -100)"
            " OR (adjustment_type = 'FIXED_PRICE' AND adjustment_value > 0)",
            name="ck_pricing_rules_adjustment_value_valid",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)  # inclusive
    end_date = Column(Date, nullable=False)    # inclusive
    adjustment_type = Column(Enum(PricingAdjustmentType), nullable=False)
    adjustment_value = Column(Numeric(12, 2), nullable=False)
    # Overlapping rules are allowed: the highest priority wins, ties go to the most recent rule
    priority = Column(Integer, nullable=False, default=0, server_default="0")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    property = relationship("Property", back_populates="pricing_rules")
