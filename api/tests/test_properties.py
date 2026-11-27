import pytest


PROPS_URL = "/properties/"


# ---------- Create ----------

async def test_create_property_admin(client, admin_headers):
    resp = await client.post(PROPS_URL, json={
        "name": "Beach House",
        "address": "Av. Costanera 100",
        "base_price": "200.00",
    }, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Beach House"
    assert data["base_price"] == "200.00"


async def test_create_property_manager(client, manager_headers):
    resp = await client.post(PROPS_URL, json={
        "name": "City Apt",
        "address": "Calle Falsa 123",
    }, headers=manager_headers)
    assert resp.status_code == 201


async def test_create_property_owner(client, owner_headers):
    resp = await client.post(PROPS_URL, json={
        "name": "Owner Prop",
        "address": "Some Address",
    }, headers=owner_headers)
    assert resp.status_code == 201


async def test_create_property_no_auth(client):
    resp = await client.post(PROPS_URL, json={
        "name": "No Auth",
        "address": "Nowhere",
    })
    assert resp.status_code == 401


# ---------- List ----------

async def test_list_properties(client, admin_headers):
    await client.post(PROPS_URL, json={"name": "P1", "address": "A1"}, headers=admin_headers)
    await client.post(PROPS_URL, json={"name": "P2", "address": "A2"}, headers=admin_headers)

    resp = await client.get(PROPS_URL, headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_list_properties_pagination(client, admin_headers):
    for i in range(5):
        await client.post(PROPS_URL, json={"name": f"P{i}", "address": f"A{i}"}, headers=admin_headers)

    resp = await client.get(PROPS_URL, params={"skip": 0, "limit": 2}, headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ---------- Get by ID ----------

async def test_get_property(client, admin_headers, test_property):
    prop_id = test_property["id"]
    resp = await client.get(f"{PROPS_URL}{prop_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == prop_id


async def test_get_property_not_found(client, admin_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"{PROPS_URL}{fake_id}", headers=admin_headers)
    assert resp.status_code == 404


# ---------- Update ----------

async def test_update_property(client, admin_headers, test_property):
    prop_id = test_property["id"]
    resp = await client.put(f"{PROPS_URL}{prop_id}", json={
        "name": "Updated Name",
    }, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


# ---------- Delete (soft) ----------

async def test_delete_property(client, admin_headers, test_property):
    prop_id = test_property["id"]
    resp = await client.delete(f"{PROPS_URL}{prop_id}", headers=admin_headers)
    assert resp.status_code == 204


# ---------- Catalog fields ----------

CATALOG_FIELDS = {
    "max_guests": 4,
    "amenities": ["Wifi", " Parrilla ", "", "Wifi"],
    "check_in_time": "14:00",
    "check_out_time": "10:30",
    "cancellation_policy": "Reembolso total hasta 7 días antes.",
    "house_rules": "No se permiten fiestas.",
}


async def test_create_property_with_catalog_fields(client, admin_headers):
    resp = await client.post(PROPS_URL, json={
        "name": "Cabaña Catálogo", "address": "Ruta 40", **CATALOG_FIELDS,
    }, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["max_guests"] == 4
    assert data["amenities"] == ["Wifi", "Parrilla"]
    assert data["check_in_time"] == "14:00:00"
    assert data["check_out_time"] == "10:30:00"
    assert data["cancellation_policy"] == CATALOG_FIELDS["cancellation_policy"]
    assert data["house_rules"] == CATALOG_FIELDS["house_rules"]


async def test_create_property_catalog_fields_default_null(client, admin_headers):
    resp = await client.post(PROPS_URL, json={"name": "Legacy", "address": "A"}, headers=admin_headers)
    data = resp.json()
    for field in ("max_guests", "amenities", "check_in_time", "check_out_time", "cancellation_policy", "house_rules"):
        assert data[field] is None


async def test_create_property_rejects_non_positive_max_guests(client, admin_headers):
    resp = await client.post(PROPS_URL, json={"name": "X", "address": "A", "max_guests": 0}, headers=admin_headers)
    assert resp.status_code == 422


async def test_update_property_catalog_fields(client, admin_headers, test_property):
    resp = await client.put(f"{PROPS_URL}{test_property['id']}", json={
        "max_guests": 6, "amenities": ["Pileta"], "house_rules": "Sin mascotas",
    }, headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_guests"] == 6
    assert data["amenities"] == ["Pileta"]
    assert data["house_rules"] == "Sin mascotas"

    # Explicit null clears a field
    resp = await client.put(f"{PROPS_URL}{test_property['id']}", json={"max_guests": None}, headers=admin_headers)
    assert resp.json()["max_guests"] is None
    assert resp.json()["amenities"] == ["Pileta"]
