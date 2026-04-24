import sys
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from api.app import app
from api.db import Base, get_db
from api.auth import hash_password
from api.misc import get_config
from api.models import UserORM, ReceiptORM, LineItemORM

_TEST_DB_URL = get_config(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost/ritter_test",
)

_VIEWS_DIR = Path(__file__).parent.parent / "sql" / "views"
_VIEW_FILES = [
    "receipt_balances.sql",
    "unsettled_summary.sql",
    "user_outstanding_totals.sql",
]


@pytest_asyncio.fixture(scope="session")
async def engine():
    e = create_async_engine(_TEST_DB_URL)
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        for fname in _VIEW_FILES:
            await conn.execute(text((_VIEWS_DIR / fname).read_text()))
    yield e
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await e.dispose()


@pytest_asyncio.fixture
async def db(engine):
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest_asyncio.fixture
async def client(db):
    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db

    with patch("api.app.setup_db", new_callable=AsyncMock), \
         patch("api.app.seed_admin", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin(db):
    user = UserORM(
        username="admin",
        hashed_password=hash_password("adminpass"),
        name="Admin",
        is_admin=True,
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def user(db):
    u = UserORM(
        username="alice",
        hashed_password=hash_password("alicepass"),
        name="Alice",
        is_admin=False,
    )
    db.add(u)
    await db.commit()
    return u


@pytest_asyncio.fixture
async def admin_token(client, admin):
    resp = await client.post("/auth/login", data={"username": "admin", "password": "adminpass"})
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def user_token(client, user):
    resp = await client.post("/auth/login", data={"username": "alice", "password": "alicepass"})
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def receipt(db, user):
    r = ReceiptORM(
        created_by_id=user.id,
        payer_id=user.id,
        participant_ids=[user.id],
    )
    db.add(r)
    await db.commit()
    return r


@pytest_asyncio.fixture
async def receipt_with_item(db, receipt):
    item = LineItemORM(
        receipt_id=receipt.id,
        description="Coffee",
        quantity=2.0,
        price=3.50,
        total=7.00,
        item_order=0,
    )
    db.add(item)
    await db.commit()
    return receipt, item
