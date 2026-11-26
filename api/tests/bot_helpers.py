"""Shared helpers for the /bot test modules."""
from datetime import timedelta

from core.time import business_today


def day(offset: int) -> str:
    """ISO date `offset` days from the business today (BUSINESS_TIMEZONE)."""
    return (business_today() + timedelta(days=offset)).isoformat()


async def create_cabin(client, headers, name, max_guests=4, base_price="100.00", **extra):
    payload = {"name": name, "address": f"{name} 123", "base_price": base_price, **extra}
    if max_guests is not None:
        payload["max_guests"] = max_guests
    resp = await client.post("/properties/", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def create_booking(client, headers, property_id, check_in, check_out, status="CONFIRMED"):
    resp = await client.post("/bookings/", json={
        "property_id": property_id, "check_in": check_in, "check_out": check_out,
        "summary": "Reserva", "status": status,
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()
