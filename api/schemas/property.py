from pydantic import BaseModel, UUID4, Field, field_validator
from datetime import datetime, time
from typing import Optional, List
from decimal import Decimal


def _clean_amenities(value: Optional[List[str]]) -> Optional[List[str]]:
    """Strip items, drop blanks and duplicates (keeping order)."""
    if value is None:
        return None
    cleaned: list[str] = []
    for item in value:
        item = item.strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


class PropertyCatalogFields(BaseModel):
    """Guest-facing catalog data (public catalog export and chatbot)."""
    max_guests: Optional[int] = Field(None, gt=0, le=100)
    amenities: Optional[List[str]] = Field(None, max_length=100)
    check_in_time: Optional[time] = None
    check_out_time: Optional[time] = None
    cancellation_policy: Optional[str] = None
    house_rules: Optional[str] = None

    @field_validator("amenities")
    @classmethod
    def clean_amenities(cls, value):
        return _clean_amenities(value)


class PropertyBase(PropertyCatalogFields):
    name: str = Field(..., min_length=1, max_length=200)
    address: str = Field(..., min_length=1)
    description: Optional[str] = None
    base_price: Decimal = Field(default=0, ge=0, description="GROSS price per night (what guest pays)")
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PropertyCreate(PropertyBase):
    owner_id: Optional[UUID4] = None


class PropertyUpdate(PropertyCatalogFields):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    address: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PropertyResponse(PropertyBase):
    id: UUID4
    manager_id: UUID4
    owner_id: Optional[UUID4]
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool
    base_price: Decimal

    class Config:
        from_attributes = True
