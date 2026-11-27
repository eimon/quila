"""T6: bot input robustness, business-timezone "today" and batched availability pricing."""
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import event

from tests.bot_helpers import create_cabin, day
from tests.conftest import test_engine

AVAILABILITY_URL = "/bot/availability"
QUOTE_URL = "/bot/quote"
HOLDS_URL = "/bot/holds"


def _hold(property_id, **extra):
    body = {
        "property_id": property_id,
        "check_in": day(10),
        "check_out": day(12),
        "guests": 2,
        "lead_name": "Ana Pérez",
        "lead_phone": "+54 9 11 5555-0000",
    }
    body.update(extra)
    return body


def _assert_invalid_input(resp, *fields):
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is False
    assert body["reason"] == "invalid_input"
    assert isinstance(body["message"], str) and body["message"]
    for field in fields:
        assert field in body["message"]


# ---------- (a) Invalid input is a 200 business outcome on /bot/* ----------

async def test_malformed_date_is_invalid_input(client, bot_headers):
    resp = await client.post(
        AVAILABILITY_URL,
        json={"check_in": "15/12/2026", "check_out": "2026-12-17", "guests": 2},
        headers=bot_headers,
    )
    _assert_invalid_input(resp, "check_in")
    assert "check_out" not in resp.json()["message"]


async def test_invalid_input_names_every_invalid_field(client, bot_headers):
    resp = await client.post(
        HOLDS_URL,
        json=_hold("not-a-uuid", guests=0, lead_email="no-es-un-email"),
        headers=bot_headers,
    )
    _assert_invalid_input(resp, "property_id", "guests", "lead_email")


async def test_invalid_json_syntax_is_invalid_input(client, bot_headers):
    resp = await client.post(
        QUOTE_URL,
        content="{not json",
        headers={**bot_headers, "Content-Type": "application/json"},
    )
    _assert_invalid_input(resp)


@pytest.mark.parametrize("lead_email", ["", "   "])
async def test_blank_lead_email_creates_hold(client, bot_headers, admin_headers, lead_email):
    cabin = await create_cabin(client, admin_headers, "Sin email", max_guests=4)
    resp = await client.post(HOLDS_URL, json=_hold(cabin["id"], lead_email=lead_email), headers=bot_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True, resp.json()

    bookings = (await client.get(f"/bookings/properties/{cabin['id']}/bookings", headers=admin_headers)).json()
    assert bookings[0]["lead_email"] is None


async def test_non_bot_routes_keep_422(client, admin_headers):
    resp = await client.post("/properties/", json={"name": ""}, headers=admin_headers)
    assert resp.status_code == 422


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer nope"}])
async def test_malformed_body_without_valid_key_is_401(client, bot_key, headers):
    bad_field = {"check_in": "15/12/2026", "check_out": "2026-12-17", "guests": 2}
    assert (await client.post(AVAILABILITY_URL, json=bad_field, headers=headers)).status_code == 401

    bad_json = {**headers, "Content-Type": "application/json"}
    assert (await client.post(AVAILABILITY_URL, content="{not json", headers=bad_json)).status_code == 401


async def test_malformed_body_with_bot_disabled_is_503(client, monkeypatch):
    from core.config import settings
    monkeypatch.setattr(settings, "BOT_API_KEY", "")
    resp = await client.post(
        AVAILABILITY_URL, content="{not json",
        headers={"Authorization": "Bearer x", "Content-Type": "application/json"},
    )
    assert resp.status_code == 503


# ---------- (b) "Today" is the business date ----------

# 01:30 UTC on Dec 16 is still 22:30 on Dec 15 in Buenos Aires (UTC-3)
UTC_TOMORROW_INSTANT = datetime(2026, 12, 16, 1, 30, tzinfo=timezone.utc)


def test_business_today_uses_business_timezone():
    from core.time import business_today
    assert business_today(UTC_TOMORROW_INSTANT) == date(2026, 12, 15)


def test_business_today_follows_setting(monkeypatch):
    from core.config import settings
    from core.time import business_today
    monkeypatch.setattr(settings, "BUSINESS_TIMEZONE", "UTC")
    assert business_today(UTC_TOMORROW_INSTANT) == date(2026, 12, 16)


async def test_check_in_today_in_business_timezone_is_valid(client, bot_headers, admin_headers, monkeypatch):
    import core.time
    await create_cabin(client, admin_headers, "Hoy local", max_guests=2)
    monkeypatch.setattr(core.time, "utc_now", lambda: UTC_TOMORROW_INSTANT)

    resp = await client.post(
        AVAILABILITY_URL,
        json={"check_in": "2026-12-15", "check_out": "2026-12-16", "guests": 2},
        headers=bot_headers,
    )
    body = resp.json()
    assert body["ok"] is True, body
    assert {o["name"] for o in body["options"]} == {"Hoy local"}

    # The day before the business date is still in the past
    resp = await client.post(
        AVAILABILITY_URL,
        json={"check_in": "2026-12-14", "check_out": "2026-12-16", "guests": 2},
        headers=bot_headers,
    )
    assert resp.json()["reason"] == "invalid_dates"


# ---------- (c) Availability prices all candidates in a constant number of queries ----------

async def _cabins_with_pricing(client, admin_headers, count: int) -> list[dict]:
    cabins = []
    for i in range(count):
        cabin = await create_cabin(client, admin_headers, f"Lote {i}", max_guests=4, base_price=f"{100 + 10 * i}.00")
        # A new base price version from mid-stay and overlapping rules with different priorities
        mod = await client.post(
            f"/properties/{cabin['id']}/base-price/modify",
            json={"value": f"{200 + i}.00", "start_date": day(12)},
            headers=admin_headers,
        )
        assert mod.status_code == 201, mod.text
        for name, start, end, kind, value, priority in [
            ("Baja", day(10), day(13), "PERCENTAGE", "10", 1),
            ("Alta", day(11), day(11), "FIXED_PRICE", f"{300 + i}.00", 5),
        ]:
            rule = await client.post(f"/properties/{cabin['id']}/pricing-rules", json={
                "name": name, "start_date": start, "end_date": end,
                "adjustment_type": kind, "adjustment_value": value, "priority": priority,
            }, headers=admin_headers)
            assert rule.status_code == 200, rule.text
        cabins.append(cabin)
    return cabins


class _QueryCounter:
    def __init__(self):
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1

    def __enter__(self):
        event.listen(test_engine.sync_engine, "before_cursor_execute", self)
        return self

    def __exit__(self, *exc):
        event.remove(test_engine.sync_engine, "before_cursor_execute", self)


async def _availability_query_count(client, bot_headers) -> tuple[int, dict]:
    stay = {"check_in": day(9), "check_out": day(14), "guests": 2}
    with _QueryCounter() as counter:
        resp = await client.post(AVAILABILITY_URL, json=stay, headers=bot_headers)
    body = resp.json()
    assert body["ok"] is True, body
    return counter.count, body


async def test_availability_totals_match_single_quotes(client, bot_headers, admin_headers):
    cabins = await _cabins_with_pricing(client, admin_headers, 3)
    _, body = await _availability_query_count(client, bot_headers)

    totals = {o["property_id"]: o["total_amount"] for o in body["options"]}
    assert set(totals) == {c["id"] for c in cabins}
    for cabin in cabins:
        quote = await client.post(QUOTE_URL, json={
            "property_id": cabin["id"], "check_in": day(9), "check_out": day(14), "guests": 2,
        }, headers=bot_headers)
        assert quote.json()["total_amount"] == totals[cabin["id"]]
    # Distinct pricing per cabin, so a mixed-up batch would not pass by accident
    assert len(set(totals.values())) == 3


async def test_availability_query_count_is_constant(client, bot_headers, admin_headers):
    await _cabins_with_pricing(client, admin_headers, 1)
    few, _ = await _availability_query_count(client, bot_headers)

    await _cabins_with_pricing(client, admin_headers, 4)  # names repeat, ids differ
    many, body = await _availability_query_count(client, bot_headers)

    assert len(body["options"]) == 5
    assert many == few


async def test_quote_properties_without_candidates_runs_no_query():
    from tests.conftest import TestAsyncSession
    from services.pricing_service import PricingService
    async with TestAsyncSession() as session:
        with _QueryCounter() as counter:
            assert await PricingService(session).quote_properties([], date(2030, 1, 1), date(2030, 1, 3)) == {}
        assert counter.count == 0


async def test_unknown_uuid_property_id_still_business_failure(client, bot_headers):
    resp = await client.post(QUOTE_URL, json={
        "property_id": str(uuid.uuid4()), "check_in": day(3), "check_out": day(4), "guests": 1,
    }, headers=bot_headers)
    assert resp.json()["reason"] == "property_not_found"
