import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.db import AsyncSessionLocal, setup_db
from api.auth import seed_admin
from api.log import configure_logging, get_logger
from api.routers import auth, users, receipts, allocations, settle
from api.routers.receipts import RECEIPT_IMAGE_PATH
from api.routers.users import PROFILE_PICTURE_PATH

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    os.makedirs(RECEIPT_IMAGE_PATH, exist_ok=True)
    os.makedirs(PROFILE_PICTURE_PATH, exist_ok=True)
    await setup_db()
    log.info("DB ready")
    async with AsyncSessionLocal() as db:
        await seed_admin(db)
    log.info("Startup complete")
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(receipts.router)
app.include_router(allocations.router)
app.include_router(settle.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
