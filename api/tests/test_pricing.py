import pytest
from datetime import date


def _rules_url(property_id: str) -> str:
    return f"/properties/{property_id}/pricing-rules"


def _rule_payload(**overrides):
    payload = {
        "name": "Summer Rule",
        "start_date": "2026-06-01",
        "end_date": "2026-08-31",
        "profitability_percent": "80.00",
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


async def test_create_pricing_rule_overlap(client, admin_headers, test_property):
    pid = test_property["id"]

    resp1 = await client.post(
        _rules_url(pid),
        json=_rule_payload(),
        headers=admin_headers,
    )
    assert resp1.status_code == 200

    # Overlapping range
    resp2 = await client.post(
        _rules_url(pid),
        json=_rule_payload(name="Another", start_date="2026-07-01", end_date="2026-09-30"),
        headers=admin_headers,
    )
    assert resp2.status_code == 400


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
