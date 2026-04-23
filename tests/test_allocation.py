import pytest
from allocation import *


# --- equal split ---

def test_equal_split_two_people():
    results = split_equal(10, [
        ParticipantShare(user_id=1),
        ParticipantShare(user_id=2),
    ])
    assert results[0].amount == pytest.approx(10 / 2)
    assert results[1].amount == pytest.approx(10 / 2)


def test_equal_split_three_people_sums_to_total():
    results = split_equal(10, [
        ParticipantShare(user_id=1),
        ParticipantShare(user_id=2),
        ParticipantShare(user_id=3),
    ])
    assert sum(r.amount for r in results) == pytest.approx(10)


def test_equal_split_one_person_gets_full_amount():
    results = split_equal(7.5, [ParticipantShare(user_id=1)])
    assert results[0].amount == pytest.approx(7.5)


def test_equal_split_third_decimal_place_sums_to_total():
    # 1.55 / 2 = 0.775 — third decimal place, must not lose a cent
    results = split_equal(1.55, [
        ParticipantShare(user_id=1),
        ParticipantShare(user_id=2),
    ])
    assert results[0].amount == pytest.approx(1.55 / 2)
    assert results[1].amount == pytest.approx(1.55 / 2)
    assert sum(r.amount for r in results) == pytest.approx(1.55)


def test_equal_split_discount_item():
    results = split_equal(-4, [
        ParticipantShare(user_id=1),
        ParticipantShare(user_id=2),
    ])
    assert results[0].amount == pytest.approx(-4 / 2)
    assert results[1].amount == pytest.approx(-4 / 2)


def test_equal_split_zero_total():
    results = split_equal(0, [
        ParticipantShare(user_id=1),
        ParticipantShare(user_id=2),
    ])
    assert all(r.amount == pytest.approx(0) for r in results)


# --- percentage split ---

def test_percentage_split_fifty_fifty():
    total = 20
    results = split_percentage(total, [
        ParticipantShare(user_id=1, value=50),
        ParticipantShare(user_id=2, value=50),
    ])
    assert results[0].amount == pytest.approx(total * 50 / 100)
    assert results[1].amount == pytest.approx(total * 50 / 100)


def test_percentage_split_seventy_thirty():
    total = 100
    results = split_percentage(total, [
        ParticipantShare(user_id=1, value=70),
        ParticipantShare(user_id=2, value=30),
    ])
    assert results[0].amount == pytest.approx(total * 70 / 100)
    assert results[1].amount == pytest.approx(total * 30 / 100)


def test_percentage_split_three_people():
    total = 60
    results = split_percentage(total, [
        ParticipantShare(user_id=1, value=20),
        ParticipantShare(user_id=2, value=30),
        ParticipantShare(user_id=3, value=50),
    ])
    assert results[0].amount == pytest.approx(total * 20 / 100)
    assert results[1].amount == pytest.approx(total * 30 / 100)
    assert results[2].amount == pytest.approx(total * 50 / 100)


def test_percentage_split_raises_when_not_100():
    with pytest.raises(ValueError, match="sum to 100"):
        split_percentage(10, [
            ParticipantShare(user_id=1, value=40),
            ParticipantShare(user_id=2, value=40),
        ])


def test_percentage_split_discount_item():
    total = -10
    results = split_percentage(total, [
        ParticipantShare(user_id=1, value=50),
        ParticipantShare(user_id=2, value=50),
    ])
    assert results[0].amount == pytest.approx(total * 50 / 100)
    assert results[1].amount == pytest.approx(total * 50 / 100)


# --- fraction split ---

def test_fraction_split_one_to_two():
    total = 9
    results = split_fraction(total, [
        ParticipantShare(user_id=1, value=1),
        ParticipantShare(user_id=2, value=2),
    ])
    assert results[0].amount == pytest.approx(total * 1 / (1 + 2))
    assert results[1].amount == pytest.approx(total * 2 / (1 + 2))


def test_fraction_split_equal_parts_matches_equal_split():
    total = 12
    results = split_fraction(total, [
        ParticipantShare(user_id=1, value=1),
        ParticipantShare(user_id=2, value=1),
        ParticipantShare(user_id=3, value=1),
    ])
    assert all(r.amount == pytest.approx(total / 3) for r in results)


def test_fraction_split_scale_invariant():
    # 1:2 and 100:200 must give identical amounts
    small = split_fraction(9, [ParticipantShare(user_id=1, value=1), ParticipantShare(user_id=2, value=2)])
    large = split_fraction(9, [ParticipantShare(user_id=1, value=100), ParticipantShare(user_id=2, value=200)])
    assert small[0].amount == pytest.approx(large[0].amount)
    assert small[1].amount == pytest.approx(large[1].amount)


def test_fraction_split_sums_to_total():
    total = 7.77
    results = split_fraction(total, [
        ParticipantShare(user_id=1, value=2),
        ParticipantShare(user_id=2, value=3),
        ParticipantShare(user_id=3, value=5),
    ])
    assert sum(r.amount for r in results) == pytest.approx(total)


def test_fraction_split_raises_on_zero_parts():
    with pytest.raises(ValueError, match="positive"):
        split_fraction(10, [
            ParticipantShare(user_id=1, value=0),
            ParticipantShare(user_id=2, value=0),
        ])


# --- resolve_allocations dispatcher ---

def test_resolve_dispatches_equal():
    total = 10
    results = resolve_allocations(total, SplitType.equal, [
        ParticipantShare(user_id=1),
        ParticipantShare(user_id=2),
    ])
    assert all(r.amount == pytest.approx(total / 2) for r in results)


def test_resolve_dispatches_percentage():
    total = 100
    results = resolve_allocations(total, SplitType.percentage, [
        ParticipantShare(user_id=1, value=60),
        ParticipantShare(user_id=2, value=40),
    ])
    assert results[0].amount == pytest.approx(total * 60 / 100)
    assert results[1].amount == pytest.approx(total * 40 / 100)


def test_resolve_dispatches_fraction():
    total = 6
    results = resolve_allocations(total, SplitType.fraction, [
        ParticipantShare(user_id=1, value=1),
        ParticipantShare(user_id=2, value=2),
    ])
    assert results[0].amount == pytest.approx(total * 1 / (1 + 2))
    assert results[1].amount == pytest.approx(total * 2 / (1 + 2))


def test_resolve_raises_on_empty_participants():
    with pytest.raises(ValueError, match="empty"):
        resolve_allocations(10, SplitType.equal, [])


# --- receipt_user_totals ---

def test_user_totals_single_item():
    totals = receipt_user_totals({
        1: [AllocationResult(user_id=1, amount=5), AllocationResult(user_id=2, amount=5)],
    })
    assert totals[1] == pytest.approx(5)
    assert totals[2] == pytest.approx(5)


def test_user_totals_across_multiple_items():
    totals = receipt_user_totals({
        1: [AllocationResult(user_id=1, amount=3), AllocationResult(user_id=2, amount=7)],
        2: [AllocationResult(user_id=1, amount=4), AllocationResult(user_id=3, amount=6)],
    })
    assert totals[1] == pytest.approx(3 + 4)
    assert totals[2] == pytest.approx(7)
    assert totals[3] == pytest.approx(6)


def test_user_totals_user_only_in_subset_of_items():
    totals = receipt_user_totals({
        1: [AllocationResult(user_id=1, amount=10)],
        2: [AllocationResult(user_id=1, amount=5), AllocationResult(user_id=2, amount=5)],
    })
    assert totals[1] == pytest.approx(10 + 5)
    assert totals[2] == pytest.approx(5)


def test_user_totals_empty():
    assert receipt_user_totals({}) == {}


# --- ocr_mismatch ---

def test_ocr_mismatch_totals_match():
    assert ocr_mismatch(45.60, 45.60) is False


def test_ocr_mismatch_within_epsilon():
    assert ocr_mismatch(45.60, 45.60 + 0.005) is False


def test_ocr_mismatch_exceeds_epsilon():
    assert ocr_mismatch(45.60, 45.60 - 0.65) is True


def test_ocr_mismatch_custom_epsilon():
    assert ocr_mismatch(10, 10 + 0.05, epsilon=0.10) is False
    assert ocr_mismatch(10, 10 + 0.15, epsilon=0.10) is True

