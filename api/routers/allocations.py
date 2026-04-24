from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from api.allocation import ParticipantShare, SplitType, resolve_allocations
from api.auth import get_current_user
from api.db import get_db
from api.log import get_logger
from api.models import ItemAllocationORM, LineItemORM, ReceiptORM
from api.routers.receipts import require_receipt_owner

log = get_logger(__name__)

router = APIRouter(prefix="/receipts", tags=["allocations"])


class _AllocationIn(BaseModel):
    split_type: SplitType
    participants: list[ParticipantShare]


class _AllocationOut(BaseModel):
    id: int
    line_item_id: int
    user_id: int
    split_type: SplitType
    split_value: float | None
    amount: float
    model_config = {"from_attributes": True}


class _SummaryEntry(BaseModel):
    user_id: int
    total_owed: float


@router.get("/{receipt_id}/items/{item_id}/allocations", response_model=list[_AllocationOut])
async def get_item_allocations(
    receipt_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    item = await db.get(LineItemORM, item_id)
    if item is None or item.receipt_id != receipt_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line item not found")

    result = await db.execute(
        select(ItemAllocationORM)
        .where(ItemAllocationORM.line_item_id == item_id)
        .order_by(ItemAllocationORM.id)
    )
    return result.scalars().all()


@router.put("/{receipt_id}/items/{item_id}/allocations", response_model=list[_AllocationOut])
async def set_item_allocations(
    receipt_id: int,
    item_id: int,
    body: _AllocationIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await require_receipt_owner(receipt_id, db, current_user)

    item = await db.get(LineItemORM, item_id)
    if item is None or item.receipt_id != receipt_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line item not found")

    try:
        results = resolve_allocations(item.total, body.split_type, body.participants)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    await db.execute(delete(ItemAllocationORM).where(ItemAllocationORM.line_item_id == item_id))

    allocs = []
    for r, p in zip(results, body.participants):
        alloc = ItemAllocationORM(
            line_item_id=item_id,
            user_id=r.user_id,
            split_type=body.split_type,
            split_value=p.value,
            amount=r.amount,
        )
        db.add(alloc)
        allocs.append(alloc)

    await db.commit()
    for a in allocs:
        await db.refresh(a)
    log.info("Item #%d allocations set by user #%d (split=%s, %d participants)",
             item_id, current_user.id, body.split_type.value, len(body.participants))
    return allocs


@router.get("/{receipt_id}/allocations", response_model=list[_AllocationOut])
async def get_receipt_allocations(
    receipt_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    receipt = await db.get(ReceiptORM, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")

    result = await db.execute(
        select(ItemAllocationORM)
        .join(LineItemORM, ItemAllocationORM.line_item_id == LineItemORM.id)
        .where(LineItemORM.receipt_id == receipt_id)
    )
    return result.scalars().all()


@router.get("/{receipt_id}/summary", response_model=list[_SummaryEntry])
async def get_receipt_summary(
    receipt_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    receipt = await db.get(ReceiptORM, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")

    result = await db.execute(
        select(ItemAllocationORM)
        .join(LineItemORM, ItemAllocationORM.line_item_id == LineItemORM.id)
        .where(LineItemORM.receipt_id == receipt_id)
    )
    allocs = result.scalars().all()

    totals: dict[int, float] = {}
    for a in allocs:
        totals[a.user_id] = totals.get(a.user_id, 0.0) + a.amount

    return [_SummaryEntry(user_id=uid, total_owed=amt) for uid, amt in totals.items()]
