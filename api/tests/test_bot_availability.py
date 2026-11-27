import uuid

import pytest

from tests.bot_helpers import create_booking, create_cabin, day

AVAILABILITY_URL = "/bot/availability"
QUOTE_URL = "/bot/quote"


def _search(check_in=None, check_out=None, guests=2):
    return {"check_in": check_in or day(10), "check_out": check_out or day(12), "guests": guests}


def _option_names(resp) -> set[str]:
    body = resp.json()
    assert resp.status_code == 200
    assert body["ok"] is True, body
    return {o["name"] for o in body["options"]}


# ---------- Auth ----------

@pytest.mark.parametrize("url,body", [
    (AVAILABILITY_URL, _search()),
    (QUOTE_URL, {**_search(), "property_id": str(uuid.uuid4())}),
])
async def test_bot_endpoints_require_key(client, bot_key, url, body):
    assert (await client.post(url, json=body)).status_code == 401
    wrong = {"Authorization": "Bearer nope"}
    assert (await client.post(url, json=body, headers=wrong)).status_code == 401


async def test_bot_endpoints_disabled_without_env_key(client, monkeypatch):
    from core.config import settings
    monkeypatch.setattr(settings, "BOT_API_KEY", "")
    resp = await client.post(AVAILABILITY_URL, json=_search(), headers={"Authorization": "Bearer x"})
    assert resp.status_code == 503


# ---------- Availability ----------

async def test_availability_returns_quote_per_option(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Cabaña Libre", max_guests=4, base_price="100.00")
    # One night at a fixed 250 inside the stay
    rule = await client.post(f"/properties/{cabin['id']}/pricing-rules", json={
        "name": "Finde", "start_date": day(11), "end_date": day(11),
        "adjustment_type": "FIXED_PRICE", "adjustment_value": "250.00", "priority": 1,
    }, headers=admin_headers)
    assert rule.status_code == 200

    resp = await client.post(AVAILABILITY_URL, json=_search(day(10), day(13), 3), headers=bot_headers)
    body = resp.json()
    assert resp.status_code == 200
    assert body["ok"] is True
    assert body["nights"] == 3
    assert body["options"] == [{
        "property_id": cabin["id"],
        "name": "Cabaña Libre",
        "max_guests": 4,
        "total_amount": "450.00",
        "nightly_average": "150.00",
    }]


async def test_availability_excludes_unavailable_cabins(client, bot_headers, admin_headers):
    free = await create_cabin(client, admin_headers, "Libre", max_guests=4)
    booked = await create_cabin(client, admin_headers, "Reservada", max_guests=4)
    held = await create_cabin(client, admin_headers, "Con hold", max_guests=4)
    inactive = await create_cabin(client, admin_headers, "Inactiva", max_guests=4)
    await create_cabin(client, admin_headers, "Chica", max_guests=1)
    await create_cabin(client, admin_headers, "Sin capacidad", max_guests=None)
    cancelled = await create_cabin(client, admin_headers, "Cancelada", max_guests=4)
    adjacent = await create_cabin(client, admin_headers, "Contigua", max_guests=4)

    await create_booking(client, admin_headers, booked["id"], day(11), day(15))
    await create_booking(client, admin_headers, held["id"], day(9), day(11), status="TENTATIVE")
    await client.delete(f"/properties/{inactive['id']}", headers=admin_headers)
    c = await create_booking(client, admin_headers, cancelled["id"], day(10), day(12))
    await client.post(f"/bookings/{c['id']}/cancel", headers=admin_headers)
    # check-out is exclusive: a stay ending on our check-in does not block
    await create_booking(client, admin_headers, adjacent["id"], day(8), day(10))
    await create_booking(client, admin_headers, adjacent["id"], day(12), day(14))

    resp = await client.post(AVAILABILITY_URL, json=_search(day(10), day(12), 2), headers=bot_headers)
    assert _option_names(resp) == {free["name"], cancelled["name"], adjacent["name"]}


async def test_availability_empty_is_ok(client, bot_headers, admin_headers):
    await create_cabin(client, admin_headers, "Chica", max_guests=2)
    resp = await client.post(AVAILABILITY_URL, json=_search(guests=5), headers=bot_headers)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "nights": 2, "options": []}


@pytest.mark.parametrize("check_in,check_out", [
    (day(-1), day(2)),   # check-in in the past
    (day(5), day(5)),    # zero nights
    (day(6), day(5)),    # check-out before check-in
])
async def test_availability_invalid_dates(client, bot_headers, check_in, check_out):
    resp = await client.post(AVAILABILITY_URL, json=_search(check_in, check_out), headers=bot_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["reason"] == "invalid_dates"
    assert body["message"]


async def test_availability_today_is_valid(client, bot_headers, admin_headers):
    await create_cabin(client, admin_headers, "Hoy", max_guests=2)
    resp = await client.post(AVAILABILITY_URL, json=_search(day(0), day(1)), headers=bot_headers)
    assert _option_names(resp) == {"Hoy"}


@pytest.mark.parametrize("body", [
    {"check_in": "2030-01-01", "check_out": "2030-01-03"},             # missing guests
    {"check_in": "2030-01-01", "check_out": "2030-01-03", "guests": 0},
    {"check_in": "01/01/2030", "check_out": "2030-01-03", "guests": 2},
])
async def test_availability_malformed_body_is_invalid_input(client, bot_headers, body):
    resp = await client.post(AVAILABILITY_URL, json=body, headers=bot_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert resp.json()["reason"] == "invalid_input"


# ---------- Quote ----------

def _quote(property_id, check_in=None, check_out=None, guests=2):
    return {"property_id": property_id, **_search(check_in, check_out, guests)}


async def test_quote_available(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Cotizada", max_guests=4, base_price="120.00")
    resp = await client.post(QUOTE_URL, json=_quote(cabin["id"], day(10), day(13)), headers=bot_headers)
    assert resp.status_code == 200
    assert resp.json() == {
        "ok": True,
        "property_id": cabin["id"],
        "name": "Cotizada",
        "nights": 3,
        "total_amount": "360.00",
        "available": True,
    }


async def test_quote_booked_dates_not_available(client, bot_headers, admin_headers):
    cabin = await create_cabin(client, admin_headers, "Ocupada", max_guests=4)
    await create_booking(client, admin_headers, cabin["id"], day(11), day(12), status="TENTATIVE")
    resp = await client.post(QUOTE_URL, json=_quote(cabin["id"], day(10), day(13)), headers=bot_headers)
    body = resp.json()
    assert body["ok"] is True
    assert body["available"] is False
    assert body["total_amount"] == "300.00"


async def test_quote_failures(client, bot_headers, admin_headers):
    small = await create_cabin(client, admin_headers, "Chica", max_guests=2)
    unknown_cap = await create_cabin(client, admin_headers, "Sin capacidad", max_guests=None)
    inactive = await create_cabin(client, admin_headers, "Inactiva", max_guests=4)
    await client.delete(f"/properties/{inactive['id']}", headers=admin_headers)

    cases = [
        (_quote(str(uuid.uuid4())), "property_not_found"),
        (_quote(inactive["id"]), "property_not_found"),
        (_quote(unknown_cap["id"]), "capacity_unknown"),
        (_quote(small["id"], guests=3), "over_capacity"),
        (_quote(small["id"], day(-2), day(1)), "invalid_dates"),
        (_quote(small["id"], day(4), day(3)), "invalid_dates"),
    ]
    for body, reason in cases:
        resp = await client.post(QUOTE_URL, json=body, headers=bot_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False, (reason, data)
        assert data["reason"] == reason
        assert isinstance(data["message"], str) and data["message"]
