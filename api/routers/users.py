import os
import secrets
import uuid
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from api.auth import (
    get_current_user,
    hash_api_key,
    hash_password,
    require_admin,
    verify_password,
)
from api.db import get_db
from api.log import get_logger
from api.misc import get_config
from api.models import ApiKeyORM, ReceiptORM, UserORM
from api.user import User

PROFILE_PICTURE_PATH = get_config("PROFILE_PICTURE_PATH", "./images/profiles")

log = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


class _SetAdminBody(BaseModel):
    is_admin: bool


class _SetNameBody(BaseModel):
    name: str


class _ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str


class _CreateApiKeyBody(BaseModel):
    name: str


class _ApiKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: datetime | None
    model_config = {"from_attributes": True}


class _CreateApiKeyOut(_ApiKeyOut):
    key: str


@router.get("", response_model=list[User])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserORM))
    return result.scalars().all()


@router.put("/me/picture", response_model=User)
async def upload_profile_picture(
    image: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    if current_user.profile_picture_path and os.path.exists(current_user.profile_picture_path):
        os.remove(current_user.profile_picture_path)

    ext = os.path.splitext(image.filename or "")[1]
    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(PROFILE_PICTURE_PATH, filename)

    contents = await image.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    current_user.profile_picture_path = file_path
    current_user.profile_picture_filename = image.filename
    current_user.profile_picture_mimetype = image.content_type
    await db.commit()
    await db.refresh(current_user)
    log.info("User #%d uploaded profile picture: %s", current_user.id, image.filename)
    return current_user


@router.delete("/me/picture", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile_picture(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    if current_user.profile_picture_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No profile picture")

    if os.path.exists(current_user.profile_picture_path):
        os.remove(current_user.profile_picture_path)

    current_user.profile_picture_path = None
    current_user.profile_picture_filename = None
    current_user.profile_picture_mimetype = None
    await db.commit()
    log.info("User #%d deleted profile picture", current_user.id)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: _ChangePasswordBody,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password incorrect",
        )
    if not body.new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password cannot be empty",
        )
    current_user.hashed_password = hash_password(body.new_password)
    await db.commit()
    log.info("User #%d changed password", current_user.id)


@router.get("/me/api-keys", response_model=list[_ApiKeyOut])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    result = await db.execute(
        select(ApiKeyORM)
        .where(ApiKeyORM.user_id == current_user.id)
        .order_by(ApiKeyORM.created_at.desc())
    )
    return result.scalars().all()


@router.post("/me/api-keys", response_model=_CreateApiKeyOut, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: _CreateApiKeyBody,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name cannot be empty",
        )
    raw_key = f"rk_{secrets.token_urlsafe(32)}"
    api_key = ApiKeyORM(
        user_id=current_user.id,
        name=name,
        key_hash=hash_api_key(raw_key),
        key_prefix=raw_key[:11],
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    log.info("User #%d created API key #%d (%r)", current_user.id, api_key.id, name)
    return _CreateApiKeyOut(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        key=raw_key,
    )


@router.delete("/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    api_key = await db.get(ApiKeyORM, key_id)
    if api_key is None or api_key.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    await db.delete(api_key)
    await db.commit()
    log.info("User #%d deleted API key #%d", current_user.id, key_id)


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(UserORM, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}/name", response_model=User)
async def set_user_name(
    user_id: int,
    body: _SetNameBody,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    user = await db.get(UserORM, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name cannot be empty")
    user.name = name
    await db.commit()
    await db.refresh(user)
    log.info("User #%d name updated to %r by user #%d", user.id, name, current_user.id)
    return user


@router.patch("/{user_id}/admin", response_model=User)
async def set_user_admin(
    user_id: int,
    body: _SetAdminBody,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
):
    user = await db.get(UserORM, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id and not body.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin privileges",
        )

    user.is_admin = body.is_admin
    await db.commit()
    await db.refresh(user)
    log.info("User #%d admin status set to %s", user.id, user.is_admin)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
):
    user = await db.get(UserORM, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    receipt_count = await db.scalar(
        select(func.count()).select_from(ReceiptORM).where(
            or_(ReceiptORM.created_by_id == user_id, ReceiptORM.payer_id == user_id)
        )
    )
    if receipt_count and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User has {receipt_count} receipt(s). Use ?force=true to delete with all associated data.",
        )

    if receipt_count:
        receipts = await db.scalars(
            select(ReceiptORM).where(
                or_(ReceiptORM.created_by_id == user_id, ReceiptORM.payer_id == user_id)
            )
        )
        for receipt in receipts:
            await db.delete(receipt)

    await db.delete(user)
    await db.commit()
    log.info("User #%d deleted by admin #%d (force=%s)", user.id, current_user.id, force)


@router.get("/{user_id}/picture")
async def get_profile_picture(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(UserORM, user_id)
    if user is None or user.profile_picture_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No profile picture")
    return FileResponse(user.profile_picture_path, media_type=user.profile_picture_mimetype)
