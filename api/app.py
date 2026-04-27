import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.db import AsyncSessionLocal, setup_db
from api.auth import get_user_via_api_key_or_token, seed_admin
from api.log import configure_logging, get_logger
from api.misc import get_config
from api.models import UserORM
from api.routers import auth, users, receipts, allocations, settle
from api.routers.receipts import RECEIPT_IMAGE_PATH
from api.routers.users import PROFILE_PICTURE_PATH

log = get_logger(__name__)

_DB_STARTUP_ATTEMPTS = 12
_DB_STARTUP_DELAY_SECONDS = 2


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    os.makedirs(RECEIPT_IMAGE_PATH, exist_ok=True)
    os.makedirs(PROFILE_PICTURE_PATH, exist_ok=True)

    last_error: Exception | None = None
    for attempt in range(1, _DB_STARTUP_ATTEMPTS + 1):
        try:
            await setup_db()
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            if attempt == _DB_STARTUP_ATTEMPTS:
                break
            log.warning(
                "Database startup attempt %s/%s failed: %s",
                attempt,
                _DB_STARTUP_ATTEMPTS,
                exc,
            )
            await asyncio.sleep(_DB_STARTUP_DELAY_SECONDS)

    if last_error is not None:
        raise last_error

    log.info("DB ready")
    async with AsyncSessionLocal() as db:
        await seed_admin(db)
    log.info("Startup complete")
    yield


app = FastAPI(lifespan=lifespan)

_cors_origins = get_config("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(receipts.router)
app.include_router(allocations.router)
app.include_router(settle.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/test")
async def test_api_key(current_user: UserORM = Depends(get_user_via_api_key_or_token)):
    return {"status": "ok", "user_id": current_user.id, "username": current_user.username}
