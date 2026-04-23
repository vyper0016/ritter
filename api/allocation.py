from __future__ import annotations
from pydantic import BaseModel
from enum import Enum


class SplitType(str, Enum):
    equal = "equal"
    percentage = "percentage"
    fraction = "fraction"


class ParticipantShare(BaseModel):
    user_id: int
    value: float | None = None  # None for equal; 0-100 for percentage; numerator for fraction


class AllocationResult(BaseModel):
    user_id: int
    amount: float


def split_equal(item_total: float, participants: list[ParticipantShare]) -> list[AllocationResult]:
    amount_each = item_total / len(participants)
    return [AllocationResult(user_id=p.user_id, amount=amount_each) for p in participants]


def split_percentage(item_total: float, participants: list[ParticipantShare]) -> list[AllocationResult]:
    total_pct = sum(p.value for p in participants)
    if abs(total_pct - 100.0) > 0.01:
        raise ValueError(f"percentages must sum to 100, got {total_pct:.4f}")
    return [AllocationResult(user_id=p.user_id, amount=item_total * p.value / 100) for p in participants]


def split_fraction(item_total: float, participants: list[ParticipantShare]) -> list[AllocationResult]:
    total_parts = sum(p.value for p in participants)
    if total_parts <= 0:
        raise ValueError("fraction values must sum to a positive number")
    return [AllocationResult(user_id=p.user_id, amount=item_total * p.value / total_parts) for p in participants]


def resolve_allocations(
    item_total: float,
    split_type: SplitType,
    participants: list[ParticipantShare],
) -> list[AllocationResult]:
    if not participants:
        raise ValueError("participants must not be empty")
    match split_type:
        case SplitType.equal:
            return split_equal(item_total, participants)
        case SplitType.percentage:
            return split_percentage(item_total, participants)
        case SplitType.fraction:
            return split_fraction(item_total, participants)


def receipt_user_totals(item_allocations: dict[int, list[AllocationResult]]) -> dict[int, float]:
    """Sum each user's amounts across all line items."""
    totals: dict[int, float] = {}
    for allocs in item_allocations.values():
        for a in allocs:
            totals[a.user_id] = totals.get(a.user_id, 0.0) + a.amount
    return totals


def ocr_mismatch(ocr_total: float, line_items_total: float, epsilon: float = 0.01) -> bool:
    """True when OCR receipt total doesn't match the sum of parsed line items."""
    return abs(ocr_total - line_items_total) > epsilon
