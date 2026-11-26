from pydantic import BaseModel, UUID4, Field, model_validator
from datetime import date, datetime
from typing import Optional
from decimal import Decimal

from core.enums import PricingAdjustmentType


def validate_adjustment(adjustment_type: PricingAdjustmentType, adjustment_value: Decimal) -> None:
    """Raises ValueError when the value is not valid for the adjustment type."""
    if adjustment_type == PricingAdjustmentType.PERCENTAGE and adjustment_value <= -100:
        raise ValueError("El porcentaje de ajuste debe ser mayor a -100")
    if adjustment_type == PricingAdjustmentType.FIXED_PRICE and adjustment_value <= 0:
        raise ValueError("El precio fijo debe ser mayor a 0")


def validate_date_range(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise ValueError("La fecha de fin no puede ser anterior a la de inicio")


class PricingRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    start_date: date
    end_date: date
    adjustment_type: PricingAdjustmentType
    adjustment_value: Decimal = Field(
        ..., max_digits=12, decimal_places=2,
        description="PERCENTAGE: % over the base price (> -100). FIXED_PRICE: nightly price (> 0).",
    )
    priority: int = Field(default=0, description="Higher wins when rules overlap")


class PricingRuleCreate(PricingRuleBase):
    @model_validator(mode="after")
    def validate_rule(self):
        validate_date_range(self.start_date, self.end_date)
        validate_adjustment(self.adjustment_type, self.adjustment_value)
        return self


class PricingRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    adjustment_type: Optional[PricingAdjustmentType] = None
    adjustment_value: Optional[Decimal] = Field(None, max_digits=12, decimal_places=2)
    priority: Optional[int] = None


class PricingRuleResponse(PricingRuleBase):
    id: UUID4
    property_id: UUID4
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
