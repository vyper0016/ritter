import pytest
from sqlalchemy import select
from api.models import ReceiptORM

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_settle_specific_receipts(client, user_token, db, receipt):
    resp = await client.post(
        "/settle",
        json={"receipt_ids": [receipt.id]},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["settled"] == 1

    await db.refresh(receipt)
    assert receipt.settled is True
    assert receipt.settled_at is not None


async def test_settle_already_settled_counts_zero(client, user_token, db, receipt):
    await client.post(
        "/settle",
        json={"receipt_ids": [receipt.id]},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    resp = await client.post(
        "/settle",
        json={"receipt_ids": [receipt.id]},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.json()["settled"] == 0


async def test_settle_all(client, user_token, db, user):
    from api.models import ReceiptORM as R
    r1 = R(created_by_id=user.id, payer_id=user.id, participant_ids=[user.id])
    r2 = R(created_by_id=user.id, payer_id=user.id, participant_ids=[user.id])
    db.add_all([r1, r2])
    await db.commit()

    resp = await client.post(
        "/settle/all",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["settled"] == 2

    for r in [r1, r2]:
        await db.refresh(r)
        assert r.settled is True


async def test_settle_nonexistent_receipt_ids(client, user_token):
    resp = await client.post(
        "/settle",
        json={"receipt_ids": [99999]},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["settled"] == 0


async def test_settle_preview_empty(client, user_token):
    resp = await client.get(
        "/settle/preview",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["receipts"] == []
    assert data["grand_totals"] == []
    assert data["any_ocr_mismatch"] is False


async def test_settle_preview_with_allocations(client, user_token, db, user, admin):
    from api.models import ReceiptORM as R, LineItemORM, ItemAllocationORM
    from api.allocation import SplitType

    r = R(
        created_by_id=admin.id,
        payer_id=admin.id,
        participant_ids=[admin.id, user.id],
        vendor_name="REWE",
        total=10.00,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)

    item = LineItemORM(receipt_id=r.id, description="Milk", total=10.00, item_order=0)
    db.add(item)
    await db.commit()
    await db.refresh(item)

    db.add_all([
        ItemAllocationORM(
            line_item_id=item.id, user_id=user.id,
            split_type=SplitType.equal, split_value=None, amount=5.00,
        ),
        ItemAllocationORM(
            line_item_id=item.id, user_id=admin.id,
            split_type=SplitType.equal, split_value=None, amount=5.00,
        ),
    ])
    await db.commit()

    resp = await client.get(
        "/settle/preview",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["receipts"]) == 1
    rp = data["receipts"][0]
    assert rp["id"] == r.id
    assert rp["vendor_name"] == "REWE"
    assert rp["total"] == pytest.approx(10.00)
    assert rp["line_items_total"] == pytest.approx(10.00)
    assert rp["ocr_mismatch"] is False
    assert rp["per_user"][str(user.id)] == pytest.approx(5.00)
    assert rp["per_user"][str(admin.id)] == pytest.approx(5.00)

    assert data["any_ocr_mismatch"] is False
    gt_by_user = {gt["user_id"]: gt for gt in data["grand_totals"]}
    assert gt_by_user[user.id]["grand_total"] == pytest.approx(5.00)
    assert gt_by_user[user.id]["payer_id"] == admin.id


async def test_settle_preview_ocr_mismatch(client, user_token, db, user, admin):
    from api.models import ReceiptORM as R, LineItemORM, ItemAllocationORM
    from api.allocation import SplitType

    r = R(
        created_by_id=admin.id,
        payer_id=admin.id,
        participant_ids=[admin.id, user.id],
        vendor_name="ALDI",
        total=20.00,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)

    item = LineItemORM(receipt_id=r.id, description="Stuff", total=18.00, item_order=0)
    db.add(item)
    await db.commit()
    await db.refresh(item)

    db.add(ItemAllocationORM(
        line_item_id=item.id, user_id=user.id,
        split_type=SplitType.equal, split_value=None, amount=9.00,
    ))
    await db.commit()

    resp = await client.get(
        "/settle/preview",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    data = resp.json()
    rp = next(x for x in data["receipts"] if x["id"] == r.id)
    assert rp["ocr_mismatch"] is True
    assert rp["line_items_total"] == pytest.approx(18.00)
    assert data["any_ocr_mismatch"] is True


async def test_settle_preview_excludes_settled(client, user_token, db, user, admin):
    from api.models import ReceiptORM as R, LineItemORM, ItemAllocationORM
    from api.allocation import SplitType
    from datetime import datetime, timezone

    r = R(
        created_by_id=admin.id,
        payer_id=admin.id,
        participant_ids=[admin.id, user.id],
        total=5.00,
        settled=True,
        settled_at=datetime.now(timezone.utc),
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)

    item = LineItemORM(receipt_id=r.id, total=5.00, item_order=0)
    db.add(item)
    await db.commit()
    await db.refresh(item)

    db.add(ItemAllocationORM(
        line_item_id=item.id, user_id=user.id,
        split_type=SplitType.equal, split_value=None, amount=5.00,
    ))
    await db.commit()

    resp = await client.get(
        "/settle/preview",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    data = resp.json()
    assert all(rp["id"] != r.id for rp in data["receipts"])
