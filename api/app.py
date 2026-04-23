import os
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from api.auth import seed_admin, verify_password, create_access_token
from api.db import get_db, AsyncSessionLocal
from api.models import UserORM
from api.routers import users, receipts
from sqlalchemy import select
from fastapi import HTTPException, status


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.getenv("RECEIPT_IMAGE_PATH", "./images"), exist_ok=True)
    async with AsyncSessionLocal() as db:
        await seed_admin(db)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(users.router)
app.include_router(receipts.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/auth/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserORM).where(UserORM.username == form.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}
