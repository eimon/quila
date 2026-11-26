from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.pricing_rule import PricingRule
from schemas.pricing_rule import PricingRuleCreate, PricingRuleUpdate
from datetime import date
import uuid


class PricingRuleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, property_id: uuid.UUID, rule_create: PricingRuleCreate) -> PricingRule:
        db_rule = PricingRule(property_id=property_id, **rule_create.model_dump())
        self.db.add(db_rule)
        await self.db.flush()
        await self.db.refresh(db_rule)
        return db_rule

    async def get_by_id(self, rule_id: uuid.UUID) -> PricingRule | None:
        result = await self.db.execute(select(PricingRule).where(PricingRule.id == rule_id))
        return result.scalars().first()

    async def get_by_property(self, property_id: uuid.UUID) -> list[PricingRule]:
        """Get all rules for a property ordered by start_date (asc)."""
        result = await self.db.execute(
            select(PricingRule)
            .where(PricingRule.property_id == property_id)
            .order_by(PricingRule.start_date.asc(), PricingRule.priority.desc())
        )
        return list(result.scalars().all())

    async def get_overlapping(
        self, property_id: uuid.UUID, range_start: date, range_end: date
    ) -> list[PricingRule]:
        """Rules covering at least one night of [range_start, range_end) (rule dates are inclusive).

        Ordered by precedence: highest priority first, then most recently created, then id
        (deterministic tie-break), so the first rule covering a date is the winning one.
        """
        result = await self.db.execute(
            select(PricingRule)
            .where(
                PricingRule.property_id == property_id,
                PricingRule.start_date < range_end,
                PricingRule.end_date >= range_start,
            )
            .order_by(
                PricingRule.priority.desc(),
                PricingRule.created_at.desc(),
                PricingRule.id.desc(),
            )
        )
        return list(result.scalars().all())

    async def update(self, rule_id: uuid.UUID, rule_update: PricingRuleUpdate) -> PricingRule | None:
        db_rule = await self.get_by_id(rule_id)
        if not db_rule:
            return None

        # Explicit nulls mean "leave unchanged": every column is NOT NULL
        update_data = rule_update.model_dump(exclude_unset=True, exclude_none=True)
        for key, value in update_data.items():
            setattr(db_rule, key, value)

        await self.db.flush()
        await self.db.refresh(db_rule)
        return db_rule

    async def delete(self, rule_id: uuid.UUID) -> bool:
        db_rule = await self.get_by_id(rule_id)
        if not db_rule:
            return False

        await self.db.delete(db_rule)
        return True
