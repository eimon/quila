from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import BotFailureReason
from models.property import Property
from repositories.booking_repository import BookingRepository
from repositories.property_repository import PropertyRepository
from schemas.bot import (
    BotAvailabilityOption,
    BotAvailabilityRequest,
    BotAvailabilityResponse,
    BotFailure,
    BotQuoteRequest,
    BotQuoteResponse,
    BotStayRequest,
)
from services.bot_outcomes import bot_failure
from services.pricing_service import PricingService


class BotService:
    """Chatbot use cases. Business failures are returned (BotFailure), never raised."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.property_repo = PropertyRepository(db)
        self.booking_repo = BookingRepository(db)
        self.pricing = PricingService(db)

    @staticmethod
    def _validate_dates(stay: BotStayRequest, today: date) -> Optional[BotFailure]:
        if stay.check_in < today or stay.check_out <= stay.check_in:
            return bot_failure(BotFailureReason.INVALID_DATES)
        return None

    async def _bookable_property(
        self, property_id, guests: int
    ) -> tuple[Optional[Property], Optional[BotFailure]]:
        """Active property that can host `guests`, or the failure explaining why not."""
        prop = await self.property_repo.get_by_id(property_id)
        if not prop or not prop.is_active:
            return None, bot_failure(BotFailureReason.PROPERTY_NOT_FOUND)
        if prop.max_guests is None:
            return None, bot_failure(BotFailureReason.CAPACITY_UNKNOWN)
        if guests > prop.max_guests:
            return None, bot_failure(BotFailureReason.OVER_CAPACITY)
        return prop, None

    async def search_availability(
        self, req: BotAvailabilityRequest, today: Optional[date] = None
    ) -> BotAvailabilityResponse | BotFailure:
        failure = self._validate_dates(req, today or date.today())
        if failure:
            return failure

        nights = (req.check_out - req.check_in).days
        candidates = await self.property_repo.get_available(req.check_in, req.check_out, req.guests)
        options = []
        for prop in candidates:
            total = await self.pricing.quote_property(prop, req.check_in, req.check_out)
            options.append(BotAvailabilityOption(
                property_id=prop.id,
                name=prop.name,
                max_guests=prop.max_guests,
                total_amount=total,
                nightly_average=round(total / Decimal(nights), 2),
            ))
        return BotAvailabilityResponse(nights=nights, options=options)

    async def quote(self, req: BotQuoteRequest, today: Optional[date] = None) -> BotQuoteResponse | BotFailure:
        failure = self._validate_dates(req, today or date.today())
        if failure:
            return failure
        prop, failure = await self._bookable_property(req.property_id, req.guests)
        if failure:
            return failure

        total = await self.pricing.quote_property(prop, req.check_in, req.check_out)
        conflicts = await self.booking_repo.check_conflicts(prop.id, req.check_in, req.check_out)
        return BotQuoteResponse(
            property_id=prop.id,
            name=prop.name,
            nights=(req.check_out - req.check_in).days,
            total_amount=total,
            available=not conflicts,
        )
