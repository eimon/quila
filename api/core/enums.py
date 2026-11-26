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


class DocumentType(str, enum.Enum):
    DU = "DU"  # Documento Único (Argentina - solo números)
    EXTRANJERO = "EXTRANJERO"  # Documento extranjero (alfanumérico)



class PricingAdjustmentType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"    # base_price * (1 + value / 100)
    FIXED_PRICE = "FIXED_PRICE"  # value replaces the nightly price
