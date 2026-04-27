from collections.abc import AsyncGenerator
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from api.log import get_logger
from api.misc import get_config

log = get_logger(__name__)

_VIEWS_DIR = Path(__file__).parent.parent / "sql" / "views"
_VIEW_FILES = [
    "receipt_balances.sql",
    "unsettled_summary.sql",
    "user_outstanding_totals.sql",
]

DATABASE_URL = get_config(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost/ritter",
)

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def setup_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text("ALTER TABLE users DROP COLUMN IF EXISTS default_participant_ids")
        )
        for fname in _VIEW_FILES:
            sql = (_VIEWS_DIR / fname).read_text()
            await conn.execute(text(sql))
    log.info("Tables and views ready")
