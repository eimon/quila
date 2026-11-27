from datetime import date, timedelta

CATALOG_URL = "/public/catalog"


async def _create(client, headers, **fields):
    resp = await client.post("/properties/", json=fields, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def test_catalog_is_public_plain_text(client):
    resp = await client.get(CATALOG_URL)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/plain; charset=utf-8"
    assert "No hay cabañas disponibles" in resp.text


async def test_catalog_lists_active_properties_with_catalog_data(client, admin_headers, admin_user):
    await _create(
        client, admin_headers,
        name="Cabaña del Lago", address="Ruta 40 km 3", description="Vista al lago.",
        base_price="150.00", max_guests=4, amenities=["Wifi", "Parrilla"],
        check_in_time="14:00", check_out_time="10:00",
        cancellation_policy="Reembolso total hasta 7 días antes.",
        house_rules="No se permiten fiestas.",
    )
    inactive = await _create(client, admin_headers, name="Cabaña Cerrada", address="X", base_price="90")
    await client.delete(f"/properties/{inactive['id']}", headers=admin_headers)

    resp = await client.get(CATALOG_URL)
    text = resp.text
    assert "## Cabaña del Lago" in text
    assert "Vista al lago." in text
    assert "Ruta 40 km 3" in text
    assert "hasta 4 huéspedes" in text
    assert "Wifi, Parrilla" in text
    assert "desde las 14:00" in text
    assert "hasta las 10:00" in text
    assert "Reembolso total hasta 7 días antes." in text
    assert "No se permiten fiestas." in text
    assert "desde $150.00 por noche" in text
    assert "Cabaña Cerrada" not in text


async def test_catalog_uses_base_price_active_today(client, admin_headers):
    """A future base price change is not advertised before it takes effect."""
    prop = await _create(client, admin_headers, name="Cabaña Precio", address="X", base_price="100.00")
    future = (date.today() + timedelta(days=30)).isoformat()
    resp = await client.post(
        f"/properties/{prop['id']}/base-price/modify",
        json={"value": "250.00", "start_date": future}, headers=admin_headers,
    )
    assert resp.status_code == 201

    text = (await client.get(CATALOG_URL)).text
    assert "desde $100.00 por noche" in text
    assert "250.00" not in text


async def test_catalog_exposes_no_sensitive_fields(client, admin_headers, admin_user, owner_user):
    prop = await _create(
        client, admin_headers, name="Cabaña Privada", address="Y", base_price="80",
        owner_id=str(owner_user.id), max_guests=2,
    )
    guest = await client.post("/guests/", json={
        "full_name": "Juan Secreto", "email": "juan.secreto@test.com",
        "document_type": "DU", "document_number": "30111222",
    }, headers=admin_headers)
    assert guest.status_code == 201
    booking = await client.post("/bookings/", json={
        "property_id": prop["id"], "guest_id": guest.json()["id"],
        "check_in": "2030-01-10", "check_out": "2030-01-12", "summary": "Reserva secreta",
    }, headers=admin_headers)
    assert booking.status_code == 201

    text = (await client.get(CATALOG_URL)).text
    assert "Cabaña Privada" in text
    for secret in (
        prop["id"], str(admin_user.id), str(owner_user.id), admin_user.email, owner_user.email,
        "@", "Juan Secreto", "30111222", "Reserva secreta", booking.json()["id"],
    ):
        assert secret not in text
