import asyncio
import os
import uuid
from datetime import date, datetime
from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from api.auth import get_current_user
from api.db import get_db, AsyncSessionLocal
from api.log import get_logger
from api.misc import get_config
from api.models import ItemAllocationORM, LineItemORM, OcrStatus, ReceiptORM
from api.ocr import get_ocr_provider

RECEIPT_IMAGE_PATH = get_config("RECEIPT_IMAGE_PATH", "./images")

log = get_logger(__name__)

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


class _ParticipantsBody(BaseModel):
    payer_id: int
    participant_ids: list[int]


class _LineItemIn(BaseModel):
    description: str | None = None
    quantity: float | None = None
    price: float | None = None
    total: float
    item_order: int | None = None
    type: str | None = None


class _LineItemEdit(BaseModel):
    description: str | None = None
    quantity: float | None = None
    price: float | None = None
    total: float | None = None
    item_order: int | None = None
    type: str | None = None


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
        if receipt is None:
            log.error("Receipt #%d not found for OCR — skipping", receipt_id)
            return
        receipt.ocr_status = OcrStatus.processing
        await db.commit()
        log.info("Receipt #%d OCR started", receipt_id)
        try:
            provider = get_ocr_provider()
            assert receipt.image_path is not None
            result = await asyncio.to_thread(provider.process_document, receipt.image_path)
            for item in result.line_items:
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
            log.info("Receipt #%d OCR done — vendor=%r total=%.2f items=%d",
                     receipt_id, receipt.vendor_name, receipt.total or 0, len(result.line_items))
        except Exception:
            receipt.ocr_status = OcrStatus.failed
            log.exception("Receipt #%d OCR failed", receipt_id)
        await db.commit()


async def require_receipt_owner(receipt_id: int, db: AsyncSession, current_user) -> ReceiptORM:
    receipt = await db.get(ReceiptORM, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    if receipt.created_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not receipt owner")
    return receipt


@router.post("", response_model=_ReceiptOut, status_code=status.HTTP_201_CREATED)
async def create_receipt(
    background_tasks: BackgroundTasks,
    payer_id: int = Form(...),
    participant_ids: list[int] = Form(default=[]),
    image: UploadFile | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    image_path = image_filename = image_mimetype = None

    if image is not None:
        ext = os.path.splitext(image.filename or "")[1]
        filename = f"{uuid.uuid4()}{ext}"
        image_path = os.path.join(RECEIPT_IMAGE_PATH, filename)
        contents = await image.read()
        with open(image_path, "wb") as f:
            f.write(contents)
        image_filename = image.filename
        image_mimetype = image.content_type

    receipt = ReceiptORM(
        created_by_id=current_user.id,
        payer_id=payer_id,
        participant_ids=participant_ids,
        image_path=image_path,
        image_filename=image_filename,
        image_mimetype=image_mimetype,
        ocr_status=OcrStatus.pending if image is not None else OcrStatus.done,
    )
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)

    if image is not None:
        background_tasks.add_task(_run_ocr, receipt.id)
        log.info("Receipt #%d created by user #%d (payer=#%d) — OCR queued", receipt.id, current_user.id, payer_id)
    else:
        log.info("Receipt #%d created manually by user #%d (payer=#%d)", receipt.id, current_user.id, payer_id)

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
    result = await db.execute(
        select(ReceiptORM)
        .options(selectinload(ReceiptORM.line_items))
        .where(ReceiptORM.id == receipt_id)
    )
    receipt = result.scalar_one_or_none()
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
    body: _ParticipantsBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    receipt = await require_receipt_owner(receipt_id, db, current_user)
    receipt.payer_id = body.payer_id
    receipt.participant_ids = body.participant_ids
    await db.commit()
    await db.refresh(receipt)
    log.info("Receipt #%d participants updated by user #%d", receipt_id, current_user.id)
    return receipt


@router.post("/{receipt_id}/items", response_model=_LineItemOut, status_code=status.HTTP_201_CREATED)
async def add_line_item(
    receipt_id: int,
    body: _LineItemIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await require_receipt_owner(receipt_id, db, current_user)
    item = LineItemORM(
        receipt_id=receipt_id,
        description=body.description,
        quantity=body.quantity,
        price=body.price,
        total=body.total,
        item_order=body.item_order,
        type=body.type,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    log.info("Receipt #%d item #%d added by user #%d", receipt_id, item.id, current_user.id)
    return item


@router.get("/{receipt_id}/items", response_model=list[_LineItemOut])
async def list_line_items(
    receipt_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    receipt = await db.get(ReceiptORM, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")

    result = await db.execute(
        select(LineItemORM)
        .where(LineItemORM.receipt_id == receipt_id)
        .order_by(LineItemORM.item_order, LineItemORM.id)
    )
    return result.scalars().all()


@router.put("/{receipt_id}/items/{item_id}", response_model=_LineItemOut)
async def edit_line_item(
    receipt_id: int,
    item_id: int,
    body: _LineItemEdit,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await require_receipt_owner(receipt_id, db, current_user)
    item = await db.get(LineItemORM, item_id)
    if item is None or item.receipt_id != receipt_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    if body.description is not None:
        item.description = body.description
    if body.quantity is not None:
        item.quantity = body.quantity
    if body.price is not None:
        item.price = body.price
    if body.item_order is not None:
        item.item_order = body.item_order
    if body.type is not None:
        item.type = body.type

    if body.total is not None and body.total != item.total:
        item.total = body.total
        await db.execute(delete(ItemAllocationORM).where(ItemAllocationORM.line_item_id == item_id))
        log.info("Receipt #%d item #%d total changed — allocations cleared", receipt_id, item_id)

    await db.commit()
    await db.refresh(item)
    log.info("Receipt #%d item #%d edited by user #%d", receipt_id, item_id, current_user.id)
    return item


@router.delete("/{receipt_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_line_item(
    receipt_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await require_receipt_owner(receipt_id, db, current_user)
    item = await db.get(LineItemORM, item_id)
    if item is None or item.receipt_id != receipt_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await db.delete(item)
    await db.commit()
    log.info("Receipt #%d item #%d deleted by user #%d", receipt_id, item_id, current_user.id)
