import asyncio
import os
import uuid
from datetime import date, datetime
from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from api.auth import get_current_user
from api.db import get_db, AsyncSessionLocal
from api.models import LineItemORM, OcrStatus, ReceiptORM
from api.ocr import get_ocr_provider

RECEIPT_IMAGE_PATH = os.getenv("RECEIPT_IMAGE_PATH", "./images")

router = APIRouter(prefix="/receipts", tags=["receipts"])


class _LineItemOut(BaseModel):
    id: int
    description: str | None
    quantity: float | None
    price: float | None
    total: float
    item_order: int | None
    type: str | None
    model_config = {"from_attributes": True}


class _ReceiptOut(BaseModel):
    id: int
    created_by_id: int
    payer_id: int
    participant_ids: list[int]
    ocr_status: str
    date: date | None
    total: float | None
    vendor_name: str | None
    settled: bool
    settled_at: datetime | None
    created_at: datetime
    image_filename: str | None
    model_config = {"from_attributes": True}


class _ReceiptDetail(_ReceiptOut):
    line_items: list[_LineItemOut]
    raw_ocr_data: dict | None


async def _run_ocr(receipt_id: int) -> None:
    async with AsyncSessionLocal() as db:
        receipt = await db.get(ReceiptORM, receipt_id)
        receipt.ocr_status = OcrStatus.processing
        await db.commit()
        try:
            provider = get_ocr_provider()
            result = await asyncio.to_thread(provider.process_document, receipt.image_path)
            for i, item in enumerate(result.line_items):
                db.add(LineItemORM(
                    receipt_id=receipt_id,
                    description=item.description or None,
                    quantity=item.quantity,
                    price=item.price,
                    total=item.total,
                    item_order=item.order,
                    type=item.type or None,
                ))
            receipt.total = result.total
            receipt.vendor_name = result.vendor.name if result.vendor else None
            receipt.date = result.date.date() if isinstance(result.date, datetime) else result.date
            receipt.raw_ocr_data = result.raw_response
            receipt.ocr_status = OcrStatus.done
        except Exception:
            receipt.ocr_status = OcrStatus.failed
        await db.commit()


@router.post("", response_model=_ReceiptOut, status_code=status.HTTP_201_CREATED)
async def create_receipt(
    background_tasks: BackgroundTasks,
    image: UploadFile,
    payer_id: int = Form(...),
    participant_ids: list[int] = Form(default=[]),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ext = os.path.splitext(image.filename or "")[1]
    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(RECEIPT_IMAGE_PATH, filename)

    contents = await image.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    receipt = ReceiptORM(
        created_by_id=current_user.id,
        payer_id=payer_id,
        participant_ids=participant_ids,
        image_path=file_path,
        image_filename=image.filename,
        image_mimetype=image.content_type,
    )
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)

    background_tasks.add_task(_run_ocr, receipt.id)
    return receipt


@router.get("", response_model=list[_ReceiptOut])
async def list_receipts(
    settled: bool | None = None,
    role: str = "all",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    uid = current_user.id
    conditions = []
    if settled is not None:
        conditions.append(ReceiptORM.settled == settled)
    if role == "uploaded":
        conditions.append(ReceiptORM.created_by_id == uid)
    elif role == "participant":
        conditions.append(ReceiptORM.participant_ids.contains([uid]))
        conditions.append(ReceiptORM.created_by_id != uid)
    else:
        conditions.append(or_(
            ReceiptORM.created_by_id == uid,
            ReceiptORM.participant_ids.contains([uid]),
        ))

    result = await db.execute(select(ReceiptORM).where(*conditions))
    return result.scalars().all()


@router.get("/{receipt_id}", response_model=_ReceiptDetail)
async def get_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    receipt = await db.get(ReceiptORM, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    return receipt


@router.get("/{receipt_id}/image")
async def get_receipt_image(
    receipt_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    receipt = await db.get(ReceiptORM, receipt_id)
    if receipt is None or receipt.image_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return FileResponse(receipt.image_path, media_type=receipt.image_mimetype)


@router.put("/{receipt_id}/participants", response_model=_ReceiptOut)
async def update_participants(
    receipt_id: int,
    payer_id: int,
    participant_ids: list[int],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    receipt = await db.get(ReceiptORM, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    if receipt.created_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not receipt owner")
    receipt.payer_id = payer_id
    receipt.participant_ids = participant_ids
    await db.commit()
    await db.refresh(receipt)
    return receipt
