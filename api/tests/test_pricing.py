import uuid

import pytest
from datetime import date, timedelta


def _rules_url(property_id: str) -> str:
    return f"/properties/{property_id}/pricing-rules"


def _rule_payload(**overrides):
    payload = {
        "name": "Summer Rule",
        "start_date": "2026-06-01",
        "end_date": "2026-08-31",
        "adjustment_type": "PERCENTAGE",
        "adjustment_value": "20.00",
        "priority": 0,
    }
    payload.update(overrides)
    return payload


# ---------- Create ----------

async def test_create_pricing_rule(client, admin_headers, test_property):
    pid = test_property["id"]
    resp = await client.post(
        _rules_url(pid),
        json=_rule_payload(),
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Summer Rule"
    assert data["property_id"] == pid


async def test_create_pricing_rule_invalid_dates(client, admin_headers, test_property):
    """end_date must be after start_date."""
    resp = await client.post(
        _rules_url(test_property["id"]),
        json=_rule_payload(start_date="2026-09-01", end_date="2026-06-01"),
        headers=admin_headers,
    )
    assert resp.status_code in (400, 422)


async def test_create_pricing_rule_returns_adjustment_fields(client, admin_headers, test_property):
    resp = await client.post(
        _rules_url(test_property["id"]),
        json=_rule_payload(adjustment_type="FIXED_PRICE", adjustment_value="250.00", priority=5),
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["adjustment_type"] == "FIXED_PRICE"
    assert data["adjustment_value"] == "250.00"
    assert data["priority"] == 5
    assert "profitability_percent" not in data


async def test_create_pricing_rule_priority_defaults_to_zero(client, admin_headers, test_property):
    payload = _rule_payload()
    payload.pop("priority")
    resp = await client.post(_rules_url(test_property["id"]), json=payload, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["priority"] == 0


async def test_create_pricing_rule_single_day(client, admin_headers, test_property):
    """start_date == end_date is a valid one-night rule."""
    resp = await client.post(
        _rules_url(test_property["id"]),
        json=_rule_payload(start_date="2027-01-10", end_date="2027-01-10"),
        headers=admin_headers,
    )
    assert resp.status_code == 200


@pytest.mark.parametrize(
    "adjustment_type, adjustment_value",
    [
        ("PERCENTAGE", "-100.00"),
        ("PERCENTAGE", "-150.00"),
        ("FIXED_PRICE", "0.00"),
        ("FIXED_PRICE", "-10.00"),
    ],
)
async def test_create_pricing_rule_invalid_adjustment(
    client, admin_headers, test_property, adjustment_type, adjustment_value
):
    resp = await client.post(
        _rules_url(test_property["id"]),
        json=_rule_payload(adjustment_type=adjustment_type, adjustment_value=adjustment_value),
        headers=admin_headers,
    )
    assert resp.status_code in (400, 422)


async def test_create_pricing_rule_negative_percentage_allowed(client, admin_headers, test_property):
    resp = await client.post(
        _rules_url(test_property["id"]),
        json=_rule_payload(adjustment_value="-25.00"),
        headers=admin_headers,
    )
    assert resp.status_code == 200


async def test_create_pricing_rule_overlap_allowed(client, admin_headers, test_property):
    pid = test_property["id"]
    resp1 = await client.post(_rules_url(pid), json=_rule_payload(), headers=admin_headers)
    assert resp1.status_code == 200

    resp2 = await client.post(
        _rules_url(pid),
        json=_rule_payload(name="Another", start_date="2026-07-01", end_date="2026-09-30", priority=1),
        headers=admin_headers,
    )
    assert resp2.status_code == 200


# ---------- List ----------

async def test_list_pricing_rules(client, admin_headers, test_property):
    pid = test_property["id"]
    await client.post(_rules_url(pid), json=_rule_payload(), headers=admin_headers)

    resp = await client.get(_rules_url(pid), headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ---------- Update ----------

async def test_update_pricing_rule(client, admin_headers, test_property):
    pid = test_property["id"]
    create_resp = await client.post(_rules_url(pid), json=_rule_payload(), headers=admin_headers)
    rule_id = create_resp.json()["id"]

    resp = await client.put(
        f"/pricing-rules/{rule_id}",
        json={"name": "Updated Rule"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Rule"


async def test_update_pricing_rule_adjustment(client, admin_headers, test_property):
    pid = test_property["id"]
    create_resp = await client.post(_rules_url(pid), json=_rule_payload(), headers=admin_headers)
    rule_id = create_resp.json()["id"]

    resp = await client.put(
        f"/pricing-rules/{rule_id}",
        json={"adjustment_type": "FIXED_PRICE", "adjustment_value": "180.00", "priority": 3},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["adjustment_type"] == "FIXED_PRICE"
    assert data["adjustment_value"] == "180.00"
    assert data["priority"] == 3


async def test_update_pricing_rule_invalid_merged_values(client, admin_headers, test_property):
    """Switching to FIXED_PRICE keeps a value that is invalid for the new type -> rejected."""
    pid = test_property["id"]
    create_resp = await client.post(
        _rules_url(pid), json=_rule_payload(adjustment_value="-20.00"), headers=admin_headers
    )
    rule_id = create_resp.json()["id"]

    resp = await client.put(
        f"/pricing-rules/{rule_id}", json={"adjustment_type": "FIXED_PRICE"}, headers=admin_headers
    )
    assert resp.status_code == 400


async def test_update_pricing_rule_invalid_dates(client, admin_headers, test_property):
    pid = test_property["id"]
    create_resp = await client.post(_rules_url(pid), json=_rule_payload(), headers=admin_headers)
    rule_id = create_resp.json()["id"]

    resp = await client.put(
        f"/pricing-rules/{rule_id}", json={"end_date": "2026-05-01"}, headers=admin_headers
    )
    assert resp.status_code == 400


# ---------- Delete ----------

async def test_delete_pricing_rule(client, admin_headers, test_property):
    pid = test_property["id"]
    create_resp = await client.post(_rules_url(pid), json=_rule_payload(), headers=admin_headers)
    rule_id = create_resp.json()["id"]

    resp = await client.delete(f"/pricing-rules/{rule_id}", headers=admin_headers)
    assert resp.status_code == 200


# ---------- Calendar ----------

async def test_pricing_calendar(client, admin_headers, test_property):
    pid = test_property["id"]
    await client.post(_rules_url(pid), json=_rule_payload(), headers=admin_headers)

    resp = await client.get(
        f"/properties/{pid}/calendar",
        params={"start_date": "2026-06-01", "end_date": "2026-06-07"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 7  # 7 days


async def test_calendar_uses_winning_rule_per_day(client, admin_headers, test_property):
    pid = test_property["id"]  # base_price 100
    await client.post(
        _rules_url(pid),
        json=_rule_payload(name="Season", start_date="2027-01-01", end_date="2027-01-31", adjustment_value="50.00"),
        headers=admin_headers,
    )
    await client.post(
        _rules_url(pid),
        json=_rule_payload(
            name="Weekend", start_date="2027-01-02", end_date="2027-01-02",
            adjustment_type="FIXED_PRICE", adjustment_value="80.00", priority=10,
        ),
        headers=admin_headers,
    )

    resp = await client.get(
        f"/properties/{pid}/calendar",
        params={"start_date": "2027-01-01", "end_date": "2027-01-03"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    days = resp.json()
    assert [(d["date"], float(d["price"]), d["rule_name"]) for d in days] == [
        ("2027-01-01", 150.0, "Season"),
        ("2027-01-02", 80.0, "Weekend"),
        ("2027-01-03", 150.0, "Season"),
    ]
    assert "floor_price" not in days[0]
    assert "profitability_percent" not in days[0]


# ---------- Price quote ----------

async def _quote(client, headers, pid, check_in, check_out):
    resp = await client.get(
        f"/properties/{pid}/price-quote",
        params={"check_in": check_in, "check_out": check_out},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


async def test_quote_without_rules_uses_base_price(client, admin_headers, test_property):
    data = await _quote(client, admin_headers, test_property["id"], "2027-01-01", "2027-01-04")
    assert data["nights"] == 3
    assert float(data["total_amount"]) == 300.0


async def test_quote_percentage_rule(client, admin_headers, test_property):
    pid = test_property["id"]
    await client.post(
        _rules_url(pid),
        json=_rule_payload(start_date="2027-01-01", end_date="2027-01-31", adjustment_value="30.00"),
        headers=admin_headers,
    )
    data = await _quote(client, admin_headers, pid, "2027-01-01", "2027-01-03")
    assert float(data["total_amount"]) == 260.0


async def test_quote_negative_percentage_rule(client, admin_headers, test_property):
    pid = test_property["id"]
    await client.post(
        _rules_url(pid),
        json=_rule_payload(start_date="2027-01-01", end_date="2027-01-31", adjustment_value="-12.50"),
        headers=admin_headers,
    )
    data = await _quote(client, admin_headers, pid, "2027-01-01", "2027-01-02")
    assert float(data["total_amount"]) == 87.5


async def test_quote_fixed_price_rule(client, admin_headers, test_property):
    pid = test_property["id"]
    await client.post(
        _rules_url(pid),
        json=_rule_payload(
            start_date="2027-01-01", end_date="2027-01-31",
            adjustment_type="FIXED_PRICE", adjustment_value="250.00",
        ),
        headers=admin_headers,
    )
    data = await _quote(client, admin_headers, pid, "2027-01-01", "2027-01-03")
    assert float(data["total_amount"]) == 500.0


async def test_quote_rule_end_date_is_inclusive(client, admin_headers, test_property):
    """A rule ending on Jan 2 prices the night of Jan 2; Jan 3 falls back to base."""
    pid = test_property["id"]
    await client.post(
        _rules_url(pid),
        json=_rule_payload(start_date="2027-01-01", end_date="2027-01-02", adjustment_value="100.00"),
        headers=admin_headers,
    )
    data = await _quote(client, admin_headers, pid, "2027-01-01", "2027-01-04")
    assert float(data["total_amount"]) == 500.0  # 200 + 200 + 100


async def test_quote_overlapping_rules_highest_priority_wins(client, admin_headers, test_property):
    pid = test_property["id"]
    await client.post(
        _rules_url(pid),
        json=_rule_payload(
            name="High", start_date="2027-01-03", end_date="2027-01-04",
            adjustment_type="FIXED_PRICE", adjustment_value="80.00", priority=5,
        ),
        headers=admin_headers,
    )
    # Created later but with lower priority: must not win on Jan 3-4
    await client.post(
        _rules_url(pid),
        json=_rule_payload(name="Low", start_date="2027-01-01", end_date="2027-01-31", adjustment_value="50.00"),
        headers=admin_headers,
    )
    data = await _quote(client, admin_headers, pid, "2027-01-01", "2027-01-06")
    assert float(data["total_amount"]) == 610.0  # 150 + 150 + 80 + 80 + 150


async def test_quote_priority_tie_most_recent_rule_wins(client, admin_headers, test_property):
    pid = test_property["id"]
    await client.post(
        _rules_url(pid),
        json=_rule_payload(name="Older", start_date="2027-01-01", end_date="2027-01-31", adjustment_value="10.00"),
        headers=admin_headers,
    )
    await client.post(
        _rules_url(pid),
        json=_rule_payload(name="Newer", start_date="2027-01-01", end_date="2027-01-31", adjustment_value="20.00"),
        headers=admin_headers,
    )
    data = await _quote(client, admin_headers, pid, "2027-01-01", "2027-01-02")
    assert float(data["total_amount"]) == 120.0


async def test_quote_percentage_applies_to_versioned_base_price(client, admin_headers, test_property):
    pid = test_property["id"]
    switch = date.today() + timedelta(days=10)
    resp = await client.post(
        f"/properties/{pid}/base-price/modify",
        json={"value": "200.00", "start_date": switch.isoformat()},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    await client.post(
        _rules_url(pid),
        json=_rule_payload(
            start_date=(switch - timedelta(days=5)).isoformat(),
            end_date=(switch + timedelta(days=5)).isoformat(),
            adjustment_value="10.00",
        ),
        headers=admin_headers,
    )
    check_in = switch - timedelta(days=1)
    data = await _quote(client, admin_headers, pid, check_in.isoformat(), (switch + timedelta(days=1)).isoformat())
    assert float(data["total_amount"]) == 330.0  # 100*1.1 + 200*1.1


# ---------- Bookings keep their snapshot ----------

async def test_rule_change_does_not_alter_existing_booking_total(client, admin_headers, test_property):
    pid = test_property["id"]
    rule = await client.post(
        _rules_url(pid),
        json=_rule_payload(start_date="2027-01-01", end_date="2027-01-31", adjustment_value="50.00"),
        headers=admin_headers,
    )
    booking = await client.post(
        "/bookings/",
        json={"property_id": pid, "check_in": "2027-01-10", "check_out": "2027-01-12", "summary": "Snapshot"},
        headers=admin_headers,
    )
    assert booking.status_code == 201
    booking_id = booking.json()["id"]
    assert float(booking.json()["total_amount"]) == 300.0

    pay = await client.post(
        f"/bookings/{booking_id}/pay",
        json={"paid_at": "2027-01-01", "payment_method": "CASH"},
        headers=admin_headers,
    )
    assert pay.status_code == 200

    # Editing and creating rules over a PAID booking is allowed
    resp = await client.put(
        f"/pricing-rules/{rule.json()['id']}",
        json={"adjustment_type": "FIXED_PRICE", "adjustment_value": "999.00"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    resp = await client.post(
        _rules_url(pid),
        json=_rule_payload(name="Extra", start_date="2027-01-11", end_date="2027-01-11", priority=9),
        headers=admin_headers,
    )
    assert resp.status_code == 200

    resp = await client.get(f"/bookings/{booking_id}", headers=admin_headers)
    assert float(resp.json()["total_amount"]) == 300.0


async def test_create_booking_fails_when_quote_fails(client, admin_headers):
    """The booking must not be stored with a null total when pricing fails."""
    resp = await client.post(
        "/bookings/",
        json={
            "property_id": str(uuid.uuid4()),
            "check_in": "2027-01-10",
            "check_out": "2027-01-12",
            "summary": "No property",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 404


# ---------- Financial summary ----------

async def test_financial_summary_empty_month(client, admin_headers, test_property):
    pid = test_property["id"]

    resp = await client.get(
        f"/properties/{pid}/financial-summary",
        params={"year": 2026, "month": 6},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_income"] == 0
    assert data["paid_income"] == 0
    assert data["pending_income"] == 0
    assert data["occupied_days"] == 0
    for removed in ("costs", "net_profit", "profit_margin_percent"):
        assert removed not in data


async def test_financial_summary_revenue_split_and_proration(client, admin_headers, test_property):
    """Paid vs pending income; a booking crossing the month end is prorated by nights."""
    pid = test_property["id"]  # base_price 100

    paid = await client.post(
        "/bookings/",
        json={"property_id": pid, "check_in": "2026-06-01", "check_out": "2026-06-03", "summary": "Paid"},
        headers=admin_headers,
    )
    assert paid.status_code == 201
    resp = await client.post(
        f"/bookings/{paid.json()['id']}/pay",
        json={"paid_at": "2026-05-20", "payment_method": "CASH", "paid_amount": "150.00"},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    # 4 nights (Jun 28 - Jul 2), total 400: 3 nights in June -> 300
    crossing = await client.post(
        "/bookings/",
        json={"property_id": pid, "check_in": "2026-06-28", "check_out": "2026-07-02", "summary": "Pending"},
        headers=admin_headers,
    )
    assert crossing.status_code == 201
    assert crossing.json()["total_amount"] == "400.00"

    resp = await client.get(
        f"/properties/{pid}/financial-summary",
        params={"year": 2026, "month": 6},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_bookings"] == 2
    assert data["occupied_days"] == 5
    assert data["paid_income"] == 150
    assert data["pending_income"] == 300
    assert data["total_income"] == 450
