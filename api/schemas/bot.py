from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, UUID4

from core.enums import BotFailureReason


class BotFailure(BaseModel):
    """Business failure for the chatbot (always HTTP 200)."""
    ok: Literal[False] = False
    reason: BotFailureReason
    message: str


class BotHealthResponse(BaseModel):
    ok: Literal[True] = True


# ---------- Requests ----------
# Dates are ISO YYYY-MM-DD; check_out is exclusive. Date order and "not in the past"
# are business outcomes (invalid_dates, HTTP 200), so they are not validated here.

class BotStayRequest(BaseModel):
    check_in: date
    check_out: date
    guests: int = Field(..., gt=0, le=100)


class BotAvailabilityRequest(BotStayRequest):
    pass


class BotQuoteRequest(BotStayRequest):
    property_id: UUID4


class BotHoldRequest(BotQuoteRequest):
    lead_name: str = Field(..., min_length=1, max_length=255)
    lead_phone: str = Field(..., min_length=3, max_length=50)
    lead_email: Optional[EmailStr] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=2000)


# ---------- Responses ----------

class BotAvailabilityOption(BaseModel):
    property_id: UUID4
    name: str
    max_guests: int
    total_amount: Decimal
    nightly_average: Decimal


class BotAvailabilityResponse(BaseModel):
    ok: Literal[True] = True
    nights: int
    options: list[BotAvailabilityOption]


class BotQuoteResponse(BaseModel):
    ok: Literal[True] = True
    property_id: UUID4
    name: str
    nights: int
    total_amount: Decimal
    available: bool


class BotHoldResponse(BaseModel):
    ok: Literal[True] = True
    hold_id: UUID4
    property_id: UUID4
    name: str
    check_in: date
    check_out: date
    nights: int
    total_amount: Decimal
    expires_at: datetime
