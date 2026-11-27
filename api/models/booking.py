import uuid
from sqlalchemy import Column, String, Date, DateTime, ForeignKey, Text, Enum, CheckConstraint, Index, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base
from core.enums import BookingStatus, BookingSource, PaymentMethod


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("check_out > check_in", name="ck_bookings_checkout_after_checkin"),
        CheckConstraint("guests > 0", name="ck_bookings_guests_positive"),
        Index("ix_bookings_property_dates", "property_id", "check_in", "check_out"),
        Index("ix_bookings_status", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # iCal identifier (must be unique and persistent)
    ical_uid = Column(String, unique=True, nullable=False, index=True)

    # Foreign keys
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False)
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.id", ondelete="SET NULL"), nullable=True)

    # Dates (DATE only, no time component for iCal compatibility)
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)

    # iCal fields
    summary = Column(String, nullable=False)  # SUMMARY
    description = Column(Text, nullable=True)  # DESCRIPTION
    status = Column(Enum(BookingStatus), default=BookingStatus.CONFIRMED, nullable=False)
    source = Column(Enum(BookingSource), default=BookingSource.DIRECT, nullable=False)

    # Amounts
    total_amount = Column(Numeric(10, 2), nullable=True)  # Calculated at creation time
    paid_amount = Column(Numeric(10, 2), nullable=True)   # Actual amount received (set when paid)

    # Payment info
    paid_at = Column(Date, nullable=True)
    payment_method = Column(Enum(PaymentMethod), nullable=True)

    # Chatbot hold: a TENTATIVE booking with expires_at becomes CANCELLED lazily once expired.
    # Accepting the hold clears expires_at; cancelling keeps it (panel shows "Vencido").
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    guests = Column(Integer, nullable=True)
    lead_name = Column(String(255), nullable=True)
    lead_phone = Column(String(50), nullable=True)
    lead_email = Column(String(255), nullable=True)

    # External sync metadata
    external_id = Column(String, nullable=True)  # ID from Airbnb/Booking
    ical_url = Column(String, nullable=True)  # Source iCal URL
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    property = relationship("Property", back_populates="bookings")
    guest = relationship("Guest", back_populates="bookings")
