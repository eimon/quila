import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Numeric, CheckConstraint, Integer, Time, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        CheckConstraint("base_price >= 0", name="ck_properties_base_price_non_negative"),
        CheckConstraint("max_guests > 0", name="ck_properties_max_guests_positive"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False, index=True)
    address = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Pricing Configuration
    base_price = Column(Numeric(10, 2), default=0, nullable=False)  # GROSS price (what guest pays)

    # Geocoordinates (from address autocomplete)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)

    # Catalog (exposed to guests and the chatbot; nullable for legacy rows)
    max_guests = Column(Integer, nullable=True)
    amenities = Column(JSON, nullable=True)  # list of strings
    check_in_time = Column(Time, nullable=True)
    check_out_time = Column(Time, nullable=True)
    cancellation_policy = Column(Text, nullable=True)
    house_rules = Column(Text, nullable=True)

    # Foreign keys
    manager_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    manager = relationship("User", foreign_keys=[manager_id], back_populates="managed_properties")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_properties")
    bookings = relationship("Booking", back_populates="property")
    pricing_rules = relationship("PricingRule", back_populates="property", cascade="all, delete-orphan")
    base_prices = relationship("PropertyBasePrice", back_populates="property", cascade="all, delete-orphan")
