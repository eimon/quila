import calendar
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import BookingStatus, PricingAdjustmentType
from exceptions.general import BadRequestException, NotFoundException
from models.pricing_rule import PricingRule
from repositories.booking_repository import BookingRepository
from repositories.pricing_rule_repository import PricingRuleRepository
from repositories.property_base_price_repository import PropertyBasePriceRepository
from repositories.property_repository import PropertyRepository
from schemas.pricing_rule import (
    PricingRuleCreate,
    PricingRuleUpdate,
    validate_adjustment,
    validate_date_range,
)


class PricingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pricing_repo = PricingRuleRepository(db)
        self.property_repo = PropertyRepository(db)
        self.base_price_repo = PropertyBasePriceRepository(db)
        self.booking_repo = BookingRepository(db)

    # ------------------------------------------------------------------ #
    # Pricing rules CRUD                                                   #
    # ------------------------------------------------------------------ #

    async def create_rule(self, property_id: uuid.UUID, rule_in: PricingRuleCreate) -> object:
        # Dates and adjustment value are validated by PricingRuleCreate.
        # Overlaps are allowed (priority resolves them) and existing bookings keep
        # their total_amount snapshot, so no booking check is needed.
        prop = await self.property_repo.get_by_id(property_id)
        if not prop:
            raise NotFoundException("Propiedad no encontrada")

        return await self.pricing_repo.create(property_id, rule_in)

    async def update_rule(self, rule_id: uuid.UUID, rule_in: PricingRuleUpdate) -> object:
        db_rule = await self.pricing_repo.get_by_id(rule_id)
        if not db_rule:
            raise NotFoundException("Regla de precio no encontrada")

        # Validate the rule as it will be after the partial update
        try:
            validate_date_range(
                rule_in.start_date or db_rule.start_date,
                rule_in.end_date or db_rule.end_date,
            )
            validate_adjustment(
                rule_in.adjustment_type or db_rule.adjustment_type,
                rule_in.adjustment_value if rule_in.adjustment_value is not None else db_rule.adjustment_value,
            )
        except ValueError as exc:
            raise BadRequestException(str(exc))

        return await self.pricing_repo.update(rule_id, rule_in)

    async def delete_rule(self, rule_id: uuid.UUID) -> bool:
        if not await self.pricing_repo.delete(rule_id):
            raise NotFoundException("Regla de precio no encontrada")
        return True

    async def list_rules_by_property(self, property_id: uuid.UUID):
        return await self.pricing_repo.get_by_property(property_id)

    # ------------------------------------------------------------------ #
    # Price helpers                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _base_price_for_date(records, ref_date: date) -> Optional[Decimal]:
        """Returns the base price value active on ref_date from a pre-fetched list."""
        for r in records:
            if (r.start_date is None or r.start_date <= ref_date) \
                    and (r.end_date is None or r.end_date >= ref_date):
                return r.value
        return None

    @staticmethod
    def _winning_rule(rules: list[PricingRule], ref_date: date) -> Optional[PricingRule]:
        """First rule covering ref_date from a list already ordered by precedence."""
        for rule in rules:
            if rule.start_date <= ref_date <= rule.end_date:
                return rule
        return None

    @staticmethod
    def _apply_rule(base_price: Decimal, rule: Optional[PricingRule]) -> Decimal:
        if rule is None:
            return base_price
        if rule.adjustment_type == PricingAdjustmentType.FIXED_PRICE:
            return rule.adjustment_value
        return base_price * (1 + rule.adjustment_value / Decimal(100))

    async def _nightly_prices(self, prop, start_date: date, end_date: date) -> list[dict]:
        """Price of each night in [start_date, end_date) with the rule that produced it.

        Base prices and rules are fetched once for the whole range and resolved in memory.
        """
        all_base_prices = await self.base_price_repo.get_overlapping(prop.id, start_date, end_date)
        rules = await self.pricing_repo.get_overlapping(prop.id, start_date, end_date)

        nights = []
        current = start_date
        while current < end_date:
            rule = self._winning_rule(rules, current)
            day_base_price = self._base_price_for_date(all_base_prices, current) or prop.base_price
            nights.append({
                "date": current,
                "price": self._apply_rule(day_base_price, rule),
                "rule": rule,
            })
            current += timedelta(days=1)
        return nights

    # ------------------------------------------------------------------ #
    # Price quote                                                          #
    # ------------------------------------------------------------------ #

    async def calculate_booking_total(
        self, property_id: uuid.UUID, check_in: date, check_out: date
    ) -> Decimal:
        """Calculate total booking price summing daily prices from check_in to check_out (exclusive)."""
        prop = await self.property_repo.get_by_id(property_id)
        if not prop:
            raise NotFoundException("Propiedad no encontrada")

        return await self.quote_property(prop, check_in, check_out)

    async def quote_property(self, prop, check_in: date, check_out: date) -> Decimal:
        """Total for an already-loaded property (avoids re-fetching it per candidate)."""
        nights = await self._nightly_prices(prop, check_in, check_out)
        return round(sum((n["price"] for n in nights), Decimal(0)), 2)

    # ------------------------------------------------------------------ #
    # Calendar                                                             #
    # ------------------------------------------------------------------ #

    async def get_calendar(self, property_id: uuid.UUID, start_date: date, end_date: date):
        prop = await self.property_repo.get_by_id(property_id)
        if not prop:
            raise NotFoundException("Propiedad no encontrada")

        await self.booking_repo.expire_stale_holds()
        bookings = await self.booking_repo.check_conflicts(property_id, start_date, end_date)
        nights = await self._nightly_prices(prop, start_date, end_date + timedelta(days=1))

        result = []
        for night in nights:
            current = night["date"]
            status = "AVAILABLE"
            for b in bookings:
                if b.check_in <= current < b.check_out:
                    status = "RESERVED"
                    break

            rule = night["rule"]
            result.append({
                "date": current,
                "price": round(night["price"], 2),
                "status": status,
                "rule_name": rule.name if rule else None,
            })

        return result

    # ------------------------------------------------------------------ #
    # Financial summary                                                    #
    # ------------------------------------------------------------------ #

    async def get_financial_summary(self, property_id: uuid.UUID, year: int, month: int):
        """Monthly revenue: booking income attributed to the nights that fall in the month.

        Each booking's amount (paid_amount when recorded, else its total_amount snapshot)
        is prorated by the share of its nights inside the month. Bookings without a stored
        total fall back to the current nightly prices.
        """
        prop = await self.property_repo.get_by_id(property_id)
        if not prop:
            raise NotFoundException("Propiedad no encontrada")

        days_in_month = calendar.monthrange(year, month)[1]
        month_start = date(year, month, 1)
        month_end = month_start + timedelta(days=days_in_month)  # exclusive

        bookings = await self.booking_repo.get_by_property(property_id, 0, 1000)
        month_bookings = [
            b for b in bookings
            if b.check_in < month_end and b.check_out > month_start
            and b.status != BookingStatus.CANCELLED
        ]

        paid_income = Decimal(0)
        pending_income = Decimal(0)
        occupied_days = 0

        for booking in month_bookings:
            nights_start = max(booking.check_in, month_start)
            nights_end = min(booking.check_out, month_end)
            nights_in_month = (nights_end - nights_start).days
            total_nights = (booking.check_out - booking.check_in).days
            occupied_days += nights_in_month

            amount = booking.paid_amount if booking.paid_amount is not None else booking.total_amount
            if amount is not None:
                income = amount * Decimal(nights_in_month) / Decimal(total_nights)
            else:
                nights = await self._nightly_prices(prop, nights_start, nights_end)
                income = sum((n["price"] for n in nights), Decimal(0))

            if booking.status == BookingStatus.PAID:
                paid_income += income
            else:
                pending_income += income

        total_income = paid_income + pending_income
        occupancy_rate = (occupied_days / days_in_month) * 100 if days_in_month > 0 else 0

        return {
            "year": year,
            "month": month,
            "days_in_month": days_in_month,
            "occupied_days": occupied_days,
            "occupancy_rate": round(occupancy_rate, 2),
            "total_bookings": len(month_bookings),
            "total_income": round(total_income, 2),
            "paid_income": round(paid_income, 2),
            "pending_income": round(pending_income, 2),
        }
