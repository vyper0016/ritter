import io
import os
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_get_defaults_empty(client, user_token):
    resp = await client.get(
        "/users/me/defaults",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_set_defaults(client, user_token, db, user):
    resp = await client.put(
        "/users/me/defaults",
        json=[user.id, 2, 3],
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == [user.id, 2, 3]

    await db.refresh(user)
    assert user.default_participant_ids == [user.id, 2, 3]


async def test_set_defaults_requires_auth(client):
    resp = await client.put("/users/me/defaults", json=[1, 2])
    assert resp.status_code == 401


async def test_upload_profile_picture(client, user_token, db, user):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    resp = await client.put(
        "/users/me/picture",
        files={"image": ("avatar.png", io.BytesIO(png), "image/png")},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["profile_picture_filename"] == "avatar.png"
    assert data["profile_picture_mimetype"] == "image/png"

    await db.refresh(user)
    assert user.profile_picture_path is not None
    assert os.path.exists(user.profile_picture_path)


async def test_upload_profile_picture_replaces_old(client, user_token, db, user):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    resp1 = await client.put(
        "/users/me/picture",
        files={"image": ("one.png", io.BytesIO(png), "image/png")},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    old_path = resp1.json()["profile_picture_path"]

    resp2 = await client.put(
        "/users/me/picture",
        files={"image": ("two.png", io.BytesIO(png), "image/png")},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["profile_picture_filename"] == "two.png"
    assert not os.path.exists(old_path)


async def test_get_profile_picture(client, user_token, user):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    await client.put(
        "/users/me/picture",
        files={"image": ("x.png", io.BytesIO(png), "image/png")},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    resp = await client.get(f"/users/{user.id}/picture")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/png")


async def test_get_profile_picture_missing(client, user):
    resp = await client.get(f"/users/{user.id}/picture")
    assert resp.status_code == 404


async def test_delete_profile_picture(client, user_token, db, user):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    await client.put(
        "/users/me/picture",
        files={"image": ("x.png", io.BytesIO(png), "image/png")},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    await db.refresh(user)
    path = user.profile_picture_path

    resp = await client.delete(
        "/users/me/picture",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 204

    await db.refresh(user)
    assert user.profile_picture_path is None
    assert not os.path.exists(path)


async def test_delete_profile_picture_none_exists(client, user_token):
    resp = await client.delete(
        "/users/me/picture",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404
