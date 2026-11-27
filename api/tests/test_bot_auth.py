import pytest

from core.config import settings

HEALTH_URL = "/bot/health"


async def test_bot_valid_key(client, bot_headers):
    resp = await client.get(HEALTH_URL, headers=bot_headers)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


async def test_bot_missing_key(client, bot_key):
    resp = await client.get(HEALTH_URL)
    assert resp.status_code == 401


@pytest.mark.parametrize("header", [
    "Bearer wrong-key",
    "Bearer test-bot-key-extra",
    "test-bot-key",
    "Basic test-bot-key",
])
async def test_bot_wrong_key(client, bot_key, header):
    resp = await client.get(HEALTH_URL, headers={"Authorization": header})
    assert resp.status_code == 401


async def test_bot_user_jwt_is_not_a_bot_key(client, bot_key, admin_headers):
    resp = await client.get(HEALTH_URL, headers=admin_headers)
    assert resp.status_code == 401


async def test_bot_disabled_when_key_unset(client, monkeypatch):
    monkeypatch.setattr(settings, "BOT_API_KEY", "")
    resp = await client.get(HEALTH_URL, headers={"Authorization": "Bearer "})
    assert resp.status_code == 503
    assert resp.json()["detail"] == "bot integration disabled"

    resp = await client.get(HEALTH_URL, headers={"Authorization": "Bearer anything"})
    assert resp.status_code == 503
