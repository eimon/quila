from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, UUID4

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
