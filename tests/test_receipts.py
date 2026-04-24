import pytest
from sqlalchemy import select


async def test_create_manual_receipt(client, user_token, user):
    resp = await client.post(
        "/receipts",
        data={"payer_id": user.id, "participant_ids": user.id},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ocr_status"] == "done"
    assert data["image_filename"] is None


async def test_list_receipts_returns_own(client, user_token, receipt):
    resp = await client.get(
        "/receipts",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()]
    assert receipt.id in ids


async def test_add_item(client, user_token, receipt):
    resp = await client.post(
        f"/receipts/{receipt.id}/items",
        json={"description": "Bread", "total": 2.50},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["total"] == pytest.approx(2.50)
    assert resp.json()["description"] == "Bread"


async def test_edit_item_same_total_keeps_allocations(client, user_token, db, receipt_with_item):
    receipt, item = receipt_with_item
    from api.models import ItemAllocationORM
    from api.allocation import SplitType

    alloc = ItemAllocationORM(
        line_item_id=item.id,
        user_id=receipt.payer_id,
        split_type=SplitType.equal,
        split_value=None,
        amount=item.total,
    )
    db.add(alloc)
    await db.commit()

    resp = await client.put(
        f"/receipts/{receipt.id}/items/{item.id}",
        json={"description": "Espresso"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200

    allocs = (await db.execute(
        select(ItemAllocationORM).where(ItemAllocationORM.line_item_id == item.id)
    )).scalars().all()
    assert len(allocs) == 1


async def test_edit_item_changed_total_clears_allocations(client, user_token, db, receipt_with_item):
    receipt, item = receipt_with_item
    from api.models import ItemAllocationORM
    from api.allocation import SplitType
    from sqlalchemy import select

    alloc = ItemAllocationORM(
        line_item_id=item.id,
        user_id=receipt.payer_id,
        split_type=SplitType.equal,
        split_value=None,
        amount=item.total,
    )
    db.add(alloc)
    await db.commit()

    resp = await client.put(
        f"/receipts/{receipt.id}/items/{item.id}",
        json={"total": 9.99},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200

    allocs = (await db.execute(
        select(ItemAllocationORM).where(ItemAllocationORM.line_item_id == item.id)
    )).scalars().all()
    assert len(allocs) == 0


async def test_delete_item(client, user_token, db, receipt_with_item):
    receipt, item = receipt_with_item
    resp = await client.delete(
        f"/receipts/{receipt.id}/items/{item.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 204

    from api.models import LineItemORM
    assert await db.get(LineItemORM, item.id) is None


async def test_non_owner_cannot_edit_item(client, admin_token, receipt_with_item):
    receipt, item = receipt_with_item
    resp = await client.put(
        f"/receipts/{receipt.id}/items/{item.id}",
        json={"description": "Hack"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403
