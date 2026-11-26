import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.time import business_today, utc_now
from core.enums import BookingSource, BookingStatus, BotFailureReason
from models.property import Property
from repositories.booking_repository import BookingRepository
from repositories.property_repository import PropertyRepository
from schemas.bot import (
    BotAvailabilityOption,
    BotAvailabilityRequest,
    BotAvailabilityResponse,
    BotFailure,
    BotHoldRequest,
    BotHoldResponse,
    BotQuoteRequest,
    BotQuoteResponse,
    BotStayRequest,
)
from schemas.booking import BookingCreate
from services.booking_service import generate_ical_uid
from services.bot_outcomes import bot_failure
from services.pricing_service import PricingService

OVERLAP_CONSTRAINT = "excl_bookings_no_overlap"


def _is_overlap_violation(exc: IntegrityError) -> bool:
    return OVERLAP_CONSTRAINT in str(exc.orig)


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
        failure = self._validate_dates(req, today or business_today())
        if failure:
            return failure

        await self.booking_repo.expire_stale_holds()
        nights = (req.check_out - req.check_in).days
        candidates = await self.property_repo.get_available(req.check_in, req.check_out, req.guests)
        # One batch for all candidates: a constant number of queries, whatever their count
        totals = await self.pricing.quote_properties(candidates, req.check_in, req.check_out)
        options = [
            BotAvailabilityOption(
                property_id=prop.id,
                name=prop.name,
                max_guests=prop.max_guests,
                total_amount=totals[prop.id],
                nightly_average=round(totals[prop.id] / Decimal(nights), 2),
            )
            for prop in candidates
        ]
        return BotAvailabilityResponse(nights=nights, options=options)

    async def quote(self, req: BotQuoteRequest, today: Optional[date] = None) -> BotQuoteResponse | BotFailure:
        failure = self._validate_dates(req, today or business_today())
        if failure:
            return failure
        await self.booking_repo.expire_stale_holds()
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

    async def create_hold(self, req: BotHoldRequest, today: Optional[date] = None) -> BotHoldResponse | BotFailure:
        """Pre-reserve a cabin: a TENTATIVE CHATBOT booking that expires after HOLD_TTL_HOURS."""
        failure = self._validate_dates(req, today or business_today())
        if failure:
            return failure
        await self.booking_repo.expire_stale_holds()
        prop, failure = await self._bookable_property(req.property_id, req.guests)
        if failure:
            return failure

        unavailable = bot_failure(BotFailureReason.UNAVAILABLE)
        if await self.booking_repo.check_conflicts(prop.id, req.check_in, req.check_out):
            return unavailable

        total = await self.pricing.quote_property(prop, req.check_in, req.check_out)
        expires_at = utc_now() + timedelta(hours=settings.HOLD_TTL_HOURS)
        booking_in = BookingCreate(
            property_id=prop.id,
            guest_id=None,
            check_in=req.check_in,
            check_out=req.check_out,
            summary=f"Hold chatbot - {req.lead_name}",
            description=req.notes,
            status=BookingStatus.TENTATIVE,
            source=BookingSource.CHATBOT,
        )
        try:
            # Savepoint: if the EXCLUDE constraint rejects a concurrent overlap, only the
            # insert is rolled back and the request transaction (expiry sweep) stays usable.
            async with self.db.begin_nested():
                hold = await self.booking_repo.create(
                    booking_in,
                    generate_ical_uid(uuid.uuid4()),
                    total_amount=total,
                    expires_at=expires_at,
                    guests=req.guests,
                    lead_name=req.lead_name,
                    lead_phone=req.lead_phone,
                    lead_email=req.lead_email,
                )
        except IntegrityError as exc:
            if _is_overlap_violation(exc):
                return unavailable
            raise

        return BotHoldResponse(
            hold_id=hold.id,
            property_id=prop.id,
            name=prop.name,
            check_in=hold.check_in,
            check_out=hold.check_out,
            nights=(hold.check_out - hold.check_in).days,
            total_amount=hold.total_amount,
            expires_at=hold.expires_at,
        )
