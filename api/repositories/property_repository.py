from datetime import date

from sqlalchemy import and_, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.enums import BookingStatus
from models.booking import Booking
from models.property import Property
from schemas.property import PropertyCreate, PropertyUpdate
import uuid

# Statuses that occupy dates (same set as BookingRepository.check_conflicts)
BLOCKING_STATUSES = (BookingStatus.CONFIRMED, BookingStatus.TENTATIVE, BookingStatus.PAID)


class PropertyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, property_create: PropertyCreate, manager_id: uuid.UUID) -> Property:
        db_property = Property(**property_create.model_dump(), manager_id=manager_id)
        self.db.add(db_property)
        await self.db.flush()  # Flush to get DB-generated values
        await self.db.refresh(db_property)  # Refresh to load defaults
        return db_property

    async def get_by_id(self, property_id: uuid.UUID) -> Property | None:
        result = await self.db.execute(select(Property).where(Property.id == property_id))
        return result.scalars().first()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Property]:
        result = await self.db.execute(select(Property).where(Property.is_active == True).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_active_ordered(self) -> list[Property]:
        """All active properties ordered by name (public catalog)."""
        result = await self.db.execute(
            select(Property).where(Property.is_active == True).order_by(Property.name, Property.id)
        )
        return list(result.scalars().all())

    async def get_available(self, check_in: date, check_out: date, guests: int) -> list[Property]:
        """Active properties with known capacity >= guests and no blocking booking
        overlapping [check_in, check_out). One query; ordered by name."""
        conflicting = exists().where(
            and_(
                Booking.property_id == Property.id,
                Booking.status.in_(BLOCKING_STATUSES),
                Booking.check_in < check_out,
                Booking.check_out > check_in,
            )
        )
        result = await self.db.execute(
            select(Property)
            .where(
                Property.is_active == True,
                Property.max_guests.is_not(None),
                Property.max_guests >= guests,
                ~conflicting,
            )
            .order_by(Property.name, Property.id)
        )
        return list(result.scalars().all())

    async def get_by_manager(self, manager_id: uuid.UUID) -> list[Property]:
        result = await self.db.execute(
            select(Property).where(Property.manager_id == manager_id, Property.is_active == True)
        )
        return list(result.scalars().all())

    async def get_by_owner(self, owner_id: uuid.UUID) -> list[Property]:
        result = await self.db.execute(
            select(Property).where(Property.owner_id == owner_id, Property.is_active == True)
        )
        return list(result.scalars().all())

    async def update(self, property_id: uuid.UUID, property_update: PropertyUpdate) -> Property | None:
        db_property = await self.get_by_id(property_id)
        if not db_property:
            return None

        update_data = property_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_property, key, value)

        await self.db.flush()  # Flush to persist changes
        await self.db.refresh(db_property)  # Refresh to get updated_at
        return db_property

    async def delete(self, property_id: uuid.UUID) -> Property | None:
        db_property = await self.get_by_id(property_id)
        if not db_property:
            return None

        db_property.is_active = False
        return db_property
