from datetime import date, time
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.property import Property
from repositories.property_base_price_repository import PropertyBasePriceRepository
from repositories.property_repository import PropertyRepository


def format_money(value: Decimal) -> str:
    return f"${value:,.2f}"


def _format_time(value: Optional[time]) -> str:
    return value.strftime("%H:%M")


class CatalogService:
    """Builds the public, guest-facing catalog of active properties.

    Only guest-facing data is exported: never ids of managers or owners, emails,
    bookings or guests.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.property_repo = PropertyRepository(db)
        self.base_price_repo = PropertyBasePriceRepository(db)

    async def build_markdown(self, today: Optional[date] = None) -> str:
        today = today or date.today()
        properties = await self.property_repo.get_active_ordered()
        prices = await self.base_price_repo.get_at_date_for_properties([p.id for p in properties], today)

        lines = ["# Catálogo de cabañas", ""]
        if not properties:
            lines.append("No hay cabañas disponibles en este momento.")
            return "\n".join(lines) + "\n"

        for prop in properties:
            lines.extend(self._property_section(prop, prices.get(prop.id, prop.base_price)))
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _property_section(prop: Property, base_price: Decimal) -> list[str]:
        lines = [f"## {prop.name}", ""]
        if prop.description:
            lines.extend([prop.description.strip(), ""])

        lines.append(f"- Dirección: {prop.address}")
        if prop.max_guests:
            lines.append(f"- Capacidad: hasta {prop.max_guests} huéspedes")
        if prop.amenities:
            lines.append(f"- Comodidades: {', '.join(prop.amenities)}")
        if prop.check_in_time:
            lines.append(f"- Check-in: desde las {_format_time(prop.check_in_time)}")
        if prop.check_out_time:
            lines.append(f"- Check-out: hasta las {_format_time(prop.check_out_time)}")
        if base_price and base_price > 0:
            lines.append(f"- Precio: desde {format_money(base_price)} por noche")
        lines.append("")

        if prop.cancellation_policy:
            lines.extend(["### Política de cancelación", "", prop.cancellation_policy.strip(), ""])
        if prop.house_rules:
            lines.extend(["### Reglas de la casa", "", prop.house_rules.strip(), ""])
        return lines
