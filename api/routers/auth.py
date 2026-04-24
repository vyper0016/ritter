from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.auth import verify_password, create_access_token, hash_password, require_admin
from api.db import get_db
from api.log import get_logger
from api.models import UserORM
from api.user import User

router = APIRouter(tags=["auth"])

log = get_logger(__name__)


class _CreateUserBody(BaseModel):
    username: str
    password: str
    name: str
    is_admin: bool = False


@router.post("/auth/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserORM).where(UserORM.username == form.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(form.password, user.hashed_password):
        log.warning("Failed login attempt for username=%r", form.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    log.info("User #%d (%s) logged in", user.id, user.username)
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: _CreateUserBody,
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(require_admin),
):
    existing = await db.execute(select(UserORM).where(UserORM.username == body.username))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username taken")
    user = UserORM(
        username=body.username,
        hashed_password=hash_password(body.password),
        name=body.name,
        is_admin=body.is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    log.info("User #%d (%s) created", user.id, user.username)
    return user
