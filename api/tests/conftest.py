import pytest
import uuid

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from main import app
from core.database import Base, get_db
from core.config import settings
from core.security import get_password_hash, create_access_token
from core.enums import UserRole

from models.user import User
from models.property import Property  # noqa: F401
from models.booking import Booking  # noqa: F401
from models.guest import Guest  # noqa: F401
from models.pricing_rule import PricingRule  # noqa: F401
from models.property_base_price import PropertyBasePrice  # noqa: F401
from models.refresh_token import RefreshToken  # noqa: F401

# ---------- Test database ----------

TEST_DATABASE_URL = settings.DATABASE_URL.replace("/quila_db", "/quila_test_db")

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestAsyncSession = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestAsyncSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------- DB lifecycle ----------

@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Same double-booking guard as migration 001 (not expressible in the ORM model)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        await conn.execute(text(
            "ALTER TABLE bookings ADD CONSTRAINT excl_bookings_no_overlap "
            "EXCLUDE USING gist (property_id WITH =, daterange(check_in, check_out) WITH &&) "
            "WHERE (status != 'CANCELLED')"
        ))
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture(autouse=True)
async def clean_tables():
    """Delete all rows after each test (children first to respect FKs)."""
    yield
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM bookings"))
        await conn.execute(text("DELETE FROM pricing_rules"))
        await conn.execute(text("DELETE FROM property_base_prices"))
        await conn.execute(text("DELETE FROM properties"))
        await conn.execute(text("DELETE FROM guests"))
        await conn.execute(text("DELETE FROM refresh_tokens"))
        await conn.execute(text("DELETE FROM users"))


# ---------- Helpers ----------

async def _create_user(role: UserRole, username: str, email: str) -> User:
    async with TestAsyncSession() as session:
        user = User(
            id=uuid.uuid4(),
            username=username,
            email=email,
            hashed_password=get_password_hash("testpass123"),
            full_name=f"Test {role.value.title()}",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def _make_token(user: User) -> str:
    return create_access_token(
        subject=str(user.id),
        claims={"role": user.role.value},
    )


# ---------- Client ----------

@pytest.fixture
async def client():
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------- User fixtures ----------

@pytest.fixture
async def admin_user():
    return await _create_user(UserRole.ADMIN, "admin_test", "admin@test.com")


@pytest.fixture
async def admin_headers(admin_user):
    return {"Authorization": f"Bearer {_make_token(admin_user)}"}


@pytest.fixture
async def manager_user():
    return await _create_user(UserRole.MANAGER, "manager_test", "manager@test.com")


@pytest.fixture
async def manager_headers(manager_user):
    return {"Authorization": f"Bearer {_make_token(manager_user)}"}


@pytest.fixture
async def owner_user():
    return await _create_user(UserRole.OWNER, "owner_test", "owner@test.com")


@pytest.fixture
async def owner_headers(owner_user):
    return {"Authorization": f"Bearer {_make_token(owner_user)}"}


# ---------- Bot fixtures ----------

BOT_TEST_KEY = "test-bot-key"


@pytest.fixture
def bot_key(monkeypatch):
    monkeypatch.setattr(settings, "BOT_API_KEY", BOT_TEST_KEY)
    return BOT_TEST_KEY


@pytest.fixture
def bot_headers(bot_key):
    return {"Authorization": f"Bearer {bot_key}"}


# ---------- Domain fixtures ----------

@pytest.fixture
async def test_property(client, admin_headers):
    resp = await client.post(
        "/properties/",
        json={
            "name": "Test Property",
            "address": "123 Test St",
            "base_price": "100.00",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()
