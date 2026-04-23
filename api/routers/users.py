from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.auth import get_current_user, require_admin, hash_password
from api.db import get_db
from api.models import UserORM
from api.user import User

router = APIRouter(prefix="/users", tags=["users"])


class _CreateBody(BaseModel):
    username: str
    password: str
    name: str
    is_admin: bool = False


@router.get("", response_model=list[User])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserORM))
    return result.scalars().all()


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: _CreateBody,
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
    return user


@router.get("/me/defaults", response_model=list[int])
async def get_defaults(current_user: UserORM = Depends(get_current_user)):
    return current_user.default_participant_ids


@router.put("/me/defaults", response_model=list[int])
async def set_defaults(
    participant_ids: list[int],
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    current_user.default_participant_ids = participant_ids
    await db.commit()
    return participant_ids


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(UserORM, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
