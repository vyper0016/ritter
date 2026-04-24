import pytest
from sqlalchemy import select
from api.models import ItemAllocationORM


async def test_set_equal_split(client, user_token, db, receipt_with_item):
    receipt, item = receipt_with_item
    resp = await client.put(
        f"/receipts/{receipt.id}/items/{item.id}/allocations",
        json={
            "split_type": "equal",
            "participants": [{"user_id": receipt.payer_id}],
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    allocs = resp.json()
    assert len(allocs) == 1
    assert allocs[0]["amount"] == item.total


async def test_set_fraction_split(client, user_token, db, receipt_with_item, admin):
    receipt, item = receipt_with_item
    resp = await client.put(
        f"/receipts/{receipt.id}/items/{item.id}/allocations",
        json={
            "split_type": "fraction",
            "participants": [
                {"user_id": receipt.payer_id, "value": 1},
                {"user_id": admin.id, "value": 2},
            ],
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    allocs = resp.json()
    amounts = {a["user_id"]: a["amount"] for a in allocs}
    assert amounts[receipt.payer_id] + amounts[admin.id] == pytest.approx(item.total)
    assert amounts[admin.id] == pytest.approx(item.total * 2 / 3)


async def test_percentage_invalid_raises_422(client, user_token, receipt_with_item):
    receipt, item = receipt_with_item
    resp = await client.put(
        f"/receipts/{receipt.id}/items/{item.id}/allocations",
        json={
            "split_type": "percentage",
            "participants": [
                {"user_id": receipt.payer_id, "value": 40},
                {"user_id": receipt.payer_id + 1, "value": 40},
            ],
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 422


async def test_set_allocations_replaces_existing(client, user_token, db, receipt_with_item, admin):
    receipt, item = receipt_with_item

    await client.put(
        f"/receipts/{receipt.id}/items/{item.id}/allocations",
        json={
            "split_type": "equal",
            "participants": [
                {"user_id": receipt.payer_id},
                {"user_id": admin.id},
            ],
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )

    resp = await client.put(
        f"/receipts/{receipt.id}/items/{item.id}/allocations",
        json={
            "split_type": "equal",
            "participants": [{"user_id": receipt.payer_id}],
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    allocs = (await db.execute(
        select(ItemAllocationORM).where(ItemAllocationORM.line_item_id == item.id)
    )).scalars().all()
    assert len(allocs) == 1


async def test_non_owner_cannot_set_allocations(client, admin_token, receipt_with_item):
    receipt, item = receipt_with_item
    resp = await client.put(
        f"/receipts/{receipt.id}/items/{item.id}/allocations",
        json={"split_type": "equal", "participants": [{"user_id": receipt.payer_id}]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403
