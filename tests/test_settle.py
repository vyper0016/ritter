from sqlalchemy import select
from api.models import ReceiptORM


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
