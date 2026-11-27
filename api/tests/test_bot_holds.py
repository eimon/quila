import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from core.config import settings
from repositories.booking_repository import BookingRepository
from tests.bot_helpers import create_booking, create_cabin, day
from tests.conftest import test_engine

HOLDS_URL = "/bot/holds"
AVAILABILITY_URL = "/bot/availability"
QUOTE_URL = "/bot/quote"


def _hold(property_id, check_in=None, check_out=None, guests=2, **extra):
    body = {
        "property_id": property_id,
        "check_in": check_in or day(10),
        "check_out": check_out or day(12),
        "guests": guests,
        "lead_name": "Ana Pérez",
        "lead_phone": "+54 9 11 5555-0000",
        "lead_email": "ana@example.com",
        "notes": "Llega tarde",
    }
    body.update(extra)
    return body


async def _expire(hold_id: str):
    """Move a hold's expiry into the past, as if its TTL elapsed."""
    async with test_engine.begin() as conn:
        await conn.execute(
            text("UPDATE bookings SET expires_at = now() - interval '1 minute' WHERE id = :id"),
            {"id": hold_id},
        )


async def _create_hold(client, bot_headers, property_id, **kwargs):
    resp = await client.post(HOLDS_URL, json=_hold(property_id, **kwargs), headers=bot_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True, body
    return body


def _names(resp) -> set[str]:
    assert resp.json()["ok"] is True
    return {o["name"] for o in resp.json()["options"]}


# ---------- Creation ----------

async def test_hold_requires_key(client, bot_key):
    resp = await client.post(HOLDS_URL, json=_hold(str(uuid.uuid4())))
    assert resp.status_code == 401


async def test_create_hold(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Cabaña Hold", max_guests=4, base_price="100.00")
    before = datetime.now(timezone.utc)
    body = await _create_hold(client, bot_headers, cabin["id"], guests=3)

    assert body["property_id"] == cabin["id"]
    assert body["name"] == "Cabaña Hold"
    assert body["check_in"] == day(10)
    assert body["check_out"] == day(12)
    assert body["nights"] == 2
    assert body["total_amount"] == "200.00"
    expires_at = datetime.fromisoformat(body["expires_at"])
    ttl = timedelta(hours=settings.HOLD_TTL_HOURS)
    assert before + ttl - timedelta(minutes=1) <= expires_at <= datetime.now(timezone.utc) + ttl

    booking = (await client.get(f"/bookings/{body['hold_id']}", headers=admin_headers)).json()
    assert booking["status"] == "TENTATIVE"
    assert booking["source"] == "CHATBOT"
    assert booking["guests"] == 3
    assert booking["lead_name"] == "Ana Pérez"
    assert booking["lead_phone"] == "+54 9 11 5555-0000"
    assert booking["lead_email"] == "ana@example.com"
    assert booking["guest_id"] is None
    assert booking["summary"] == "Hold chatbot - Ana Pérez"
    assert booking["description"] == "Llega tarde"
    assert booking["total_amount"] == "200.00"
    assert booking["expires_at"] is not None


async def test_hold_ttl_is_configurable(client, bot_headers, admin_headers, monkeypatch):
    monkeypatch.setattr(settings, "HOLD_TTL_HOURS", 2)
    cabin = await create_cabin(client, admin_headers, "TTL", max_guests=2)
    body = await _create_hold(client, bot_headers, cabin["id"], lead_email=None, notes=None)
    remaining = datetime.fromisoformat(body["expires_at"]) - datetime.now(timezone.utc)
    assert timedelta(hours=1, minutes=59) <= remaining <= timedelta(hours=2)


async def test_live_hold_blocks_dates(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Bloqueada", max_guests=4)
    await _create_hold(client, bot_headers, cabin["id"])

    resp = await client.post(AVAILABILITY_URL, json={"check_in": day(11), "check_out": day(13), "guests": 2}, headers=bot_headers)
    assert _names(resp) == set()
    quote = await client.post(QUOTE_URL, json={"property_id": cabin["id"], "check_in": day(10), "check_out": day(12), "guests": 2}, headers=bot_headers)
    assert quote.json()["available"] is False

    again = await client.post(HOLDS_URL, json=_hold(cabin["id"], day(11), day(14)), headers=bot_headers)
    assert again.status_code == 200
    assert again.json()["ok"] is False
    assert again.json()["reason"] == "unavailable"


async def test_hold_exclusion_constraint_race_is_unavailable(client, bot_headers, admin_headers, monkeypatch):
    """If the pre-check misses a concurrent booking, the EXCLUDE constraint still wins."""
    cabin = await create_cabin(client, admin_headers, "Carrera", max_guests=4)
    await create_booking(client, admin_headers, cabin["id"], day(10), day(12))

    async def no_conflicts(self, *args, **kwargs):
        return []
    monkeypatch.setattr(BookingRepository, "check_conflicts", no_conflicts)

    resp = await client.post(HOLDS_URL, json=_hold(cabin["id"]), headers=bot_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert resp.json()["reason"] == "unavailable"

    monkeypatch.undo()
    bookings = (await client.get(f"/bookings/properties/{cabin['id']}/bookings", headers=admin_headers)).json()
    assert len(bookings) == 1


@pytest.mark.parametrize("overrides,reason", [
    ({"guests": 5}, "over_capacity"),
    ({"check_in": day(-1), "check_out": day(2)}, "invalid_dates"),
    ({"check_in": day(3), "check_out": day(3)}, "invalid_dates"),
    ({"property_id": str(uuid.uuid4())}, "property_not_found"),
])
async def test_hold_business_failures(client, bot_headers, admin_headers, overrides, reason):
    cabin = await create_cabin(client, admin_headers, "Validada", max_guests=4)
    resp = await client.post(HOLDS_URL, json={**_hold(cabin["id"]), **overrides}, headers=bot_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert resp.json()["reason"] == reason
    assert resp.json()["message"]


async def test_hold_capacity_unknown(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Sin capacidad", max_guests=None)
    resp = await client.post(HOLDS_URL, json=_hold(cabin["id"]), headers=bot_headers)
    assert resp.json()["reason"] == "capacity_unknown"


@pytest.mark.parametrize("overrides", [
    {"lead_name": ""},
    {"lead_phone": None},
    {"lead_email": "no-es-un-email"},
])
async def test_hold_malformed_body_is_invalid_input(client, bot_headers, overrides):
    resp = await client.post(HOLDS_URL, json={**_hold(str(uuid.uuid4())), **overrides}, headers=bot_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert resp.json()["reason"] == "invalid_input"
    assert next(iter(overrides)) in resp.json()["message"]


# ---------- Lazy expiry ----------

async def test_expired_hold_frees_dates_and_can_be_held_again(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Vencible", max_guests=4)
    first = await _create_hold(client, bot_headers, cabin["id"])
    await _expire(first["hold_id"])

    resp = await client.post(AVAILABILITY_URL, json={"check_in": day(10), "check_out": day(12), "guests": 2}, headers=bot_headers)
    assert _names(resp) == {"Vencible"}

    second = await _create_hold(client, bot_headers, cabin["id"])
    assert second["hold_id"] != first["hold_id"]

    old = (await client.get(f"/bookings/{first['hold_id']}", headers=admin_headers)).json()
    assert old["status"] == "CANCELLED"
    assert old["expires_at"] is not None  # expiry is kept for the panel ("Vencido")


async def test_quote_sweeps_expired_holds(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Cotizable", max_guests=4)
    hold = await _create_hold(client, bot_headers, cabin["id"])
    await _expire(hold["hold_id"])
    quote = await client.post(QUOTE_URL, json={"property_id": cabin["id"], "check_in": day(10), "check_out": day(12), "guests": 2}, headers=bot_headers)
    assert quote.json()["available"] is True


async def test_expiry_ignores_tentative_bookings_without_expiry(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Tentativa", max_guests=4)
    manual = await create_booking(client, admin_headers, cabin["id"], day(10), day(12), status="TENTATIVE")
    resp = await client.post(AVAILABILITY_URL, json={"check_in": day(10), "check_out": day(12), "guests": 2}, headers=bot_headers)
    assert _names(resp) == set()
    booking = (await client.get(f"/bookings/{manual['id']}", headers=admin_headers)).json()
    assert booking["status"] == "TENTATIVE"
    assert booking["expires_at"] is None


async def test_panel_booking_create_sweeps_expired_hold(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Panel", max_guests=4)
    hold = await _create_hold(client, bot_headers, cabin["id"])
    await _expire(hold["hold_id"])
    await create_booking(client, admin_headers, cabin["id"], day(10), day(12))


async def test_panel_booking_update_sweeps_expired_hold(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Mover", max_guests=4)
    hold = await _create_hold(client, bot_headers, cabin["id"])
    other = await create_booking(client, admin_headers, cabin["id"], day(20), day(22))
    await _expire(hold["hold_id"])
    resp = await client.put(f"/bookings/{other['id']}", json={"check_in": day(10), "check_out": day(12)}, headers=admin_headers)
    assert resp.status_code == 200


async def test_calendar_sweeps_expired_hold(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Calendario", max_guests=4)
    hold = await _create_hold(client, bot_headers, cabin["id"])
    cal = await client.get(f"/properties/{cabin['id']}/calendar", params={"start_date": day(10), "end_date": day(11)}, headers=admin_headers)
    assert cal.json()[0]["status"] == "RESERVED"

    await _expire(hold["hold_id"])
    cal = await client.get(f"/properties/{cabin['id']}/calendar", params={"start_date": day(10), "end_date": day(11)}, headers=admin_headers)
    assert cal.json()[0]["status"] == "AVAILABLE"
    booking = (await client.get(f"/bookings/{hold['hold_id']}", headers=admin_headers)).json()
    assert booking["status"] == "CANCELLED"


# ---------- Human conversion ----------

async def test_accept_hold_clears_expiry(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Aceptada", max_guests=4)
    hold = await _create_hold(client, bot_headers, cabin["id"])
    resp = await client.post(f"/bookings/{hold['hold_id']}/accept", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "CONFIRMED"
    assert resp.json()["expires_at"] is None


async def test_cancel_hold_keeps_expiry(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Cancelada", max_guests=4)
    hold = await _create_hold(client, bot_headers, cabin["id"])
    resp = await client.post(f"/bookings/{hold['hold_id']}/cancel", headers=admin_headers)
    assert resp.json()["status"] == "CANCELLED"
    assert resp.json()["expires_at"] is not None


async def test_expired_hold_cannot_be_accepted(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Tarde", max_guests=4)
    hold = await _create_hold(client, bot_headers, cabin["id"])
    await _expire(hold["hold_id"])
    resp = await client.post(f"/bookings/{hold['hold_id']}/accept", headers=admin_headers)
    assert resp.status_code == 400
