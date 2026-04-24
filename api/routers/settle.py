from datetime import date, datetime, timezone
from typing import cast
from pydantic import BaseModel
from fastapi import APIRouter, Depends, status
from sqlalchemy import text, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from api.auth import get_current_user
from api.db import get_db
from api.log import get_logger
from api.models import ReceiptORM

router = APIRouter(prefix="/settle", tags=["settle"])

log = get_logger(__name__)


class _ReceiptPreview(BaseModel):
    id: int
    vendor_name: str | None
    date: date | None
    total: float | None
    line_items_total: float
    payer_id: int
    per_user: dict[int, float]
    ocr_mismatch: bool


class _GrandTotalEntry(BaseModel):
    user_id: int
    payer_id: int
    grand_total: float


class _Preview(BaseModel):
    receipts: list[_ReceiptPreview]
    grand_totals: list[_GrandTotalEntry]
    any_ocr_mismatch: bool


class _SettleBody(BaseModel):
    receipt_ids: list[int]


@router.get("/preview", response_model=_Preview)
async def settle_preview(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    rows = (await db.execute(text(
        "SELECT id, vendor_name, date, total, payer_id, "
        "       user_id, total_owed, ocr_mismatch, line_items_total "
        "FROM unsettled_summary ORDER BY id"
    ))).mappings().all()

    receipts: dict[int, _ReceiptPreview] = {}
    for r in rows:
        if r["id"] not in receipts:
            receipts[r["id"]] = _ReceiptPreview(
                id=r["id"],
                vendor_name=r["vendor_name"],
                date=r["date"],
                total=r["total"],
                line_items_total=r["line_items_total"],
                payer_id=r["payer_id"],
                per_user={},
                ocr_mismatch=bool(r["ocr_mismatch"]),
            )
        receipts[r["id"]].per_user[r["user_id"]] = r["total_owed"]

    gt_rows = (await db.execute(text(
        "SELECT user_id, payer_id, grand_total FROM user_outstanding_totals"
    ))).mappings().all()

    receipt_list = list(receipts.values())
    return _Preview(
        receipts=receipt_list,
        grand_totals=[_GrandTotalEntry(**r) for r in gt_rows],
        any_ocr_mismatch=any(r.ocr_mismatch for r in receipt_list),
    )


async def _mark_settled(db: AsyncSession, where_clause) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(ReceiptORM)
        .where(ReceiptORM.settled.is_(False), where_clause)
        .values(settled=True, settled_at=now)
    )
    await db.commit()
    return cast(CursorResult, result).rowcount


@router.post("", status_code=status.HTTP_200_OK)
async def settle(
    body: _SettleBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    count = await _mark_settled(db, ReceiptORM.id.in_(body.receipt_ids))
    log.info("User #%d settled %d receipt(s): %s", current_user.id, count, body.receipt_ids)
    return {"settled": count}


@router.post("/all", status_code=status.HTTP_200_OK)
async def settle_all(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    count = await _mark_settled(db, ReceiptORM.id.isnot(None))
    log.info("User #%d settled all (%d receipts)", current_user.id, count)
    return {"settled": count}
