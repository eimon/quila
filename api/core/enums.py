import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    OWNER = "owner"


class BookingStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    TENTATIVE = "TENTATIVE"
    CANCELLED = "CANCELLED"
    PAID = "PAID"


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    TRANSFER = "TRANSFER"
    CARD = "CARD"
    OTHER = "OTHER"


class BookingSource(str, enum.Enum):
    AIRBNB = "AIRBNB"
    BOOKING = "BOOKING"
    DIRECT = "DIRECT"
    MANUAL = "MANUAL"
    CHATBOT = "CHATBOT"  # hold created by the chatbot (TENTATIVE + expires_at)


class DocumentType(str, enum.Enum):
    DU = "DU"  # Documento Único (Argentina - solo números)
    EXTRANJERO = "EXTRANJERO"  # Documento extranjero (alfanumérico)



class PricingAdjustmentType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"    # base_price * (1 + value / 100)
    FIXED_PRICE = "FIXED_PRICE"  # value replaces the nightly price


class BotFailureReason(str, enum.Enum):
    """Business outcome codes returned to the chatbot with HTTP 200 and ok=false."""
    UNAVAILABLE = "unavailable"
    OVER_CAPACITY = "over_capacity"
    INVALID_DATES = "invalid_dates"
    PROPERTY_NOT_FOUND = "property_not_found"
    CAPACITY_UNKNOWN = "capacity_unknown"
