import os
import uuid
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.auth import get_current_user, require_admin
from api.db import get_db
from api.log import get_logger
from api.misc import get_config
from api.models import UserORM
from api.user import User

PROFILE_PICTURE_PATH = get_config("PROFILE_PICTURE_PATH", "./images/profiles")

log = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


class _SetAdminBody(BaseModel):
    is_admin: bool


@router.get("", response_model=list[User])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserORM))
    return result.scalars().all()


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


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(UserORM, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
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

    await db.delete(user)
    await db.commit()
    log.info("User #%d deleted by admin #%d", user.id, current_user.id)


@router.get("/{user_id}/picture")
async def get_profile_picture(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(UserORM, user_id)
    if user is None or user.profile_picture_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No profile picture")
    return FileResponse(user.profile_picture_path, media_type=user.profile_picture_mimetype)
