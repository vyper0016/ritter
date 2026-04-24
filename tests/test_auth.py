import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_login_success(client, admin):
    resp = await client.post("/auth/login", data={"username": "admin", "password": "adminpass"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client, admin):
    resp = await client.post("/auth/login", data={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


async def test_login_unknown_user(client):
    resp = await client.post("/auth/login", data={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


async def test_protected_route_requires_token(client):
    resp = await client.get("/receipts")
    assert resp.status_code == 401


async def test_create_user_as_admin(client, admin_token):
    resp = await client.post(
        "/users",
        json={"username": "bob", "password": "bobpass", "name": "Bob"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "bob"


async def test_create_user_requires_admin(client, user_token):
    resp = await client.post(
        "/users",
        json={"username": "eve", "password": "evepass", "name": "Eve"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


async def test_create_user_duplicate_username(client, admin_token, admin):
    resp = await client.post(
        "/users",
        json={"username": "admin", "password": "x", "name": "Dupe"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


async def test_set_user_admin_as_admin(client, admin_token, user):
    resp = await client.patch(
        f"/users/{user.id}/admin",
        json={"is_admin": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is True


async def test_set_user_admin_requires_admin(client, user_token, admin):
    resp = await client.patch(
        f"/users/{admin.id}/admin",
        json={"is_admin": False},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


async def test_set_user_admin_cannot_demote_self(client, admin_token, admin):
    resp = await client.patch(
        f"/users/{admin.id}/admin",
        json={"is_admin": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


async def test_delete_user_as_admin(client, admin_token):
    created = await client.post(
        "/users",
        json={"username": "charlie", "password": "charliepass", "name": "Charlie"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = created.json()["id"]

    resp = await client.delete(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204

    check = await client.get(f"/users/{user_id}")
    assert check.status_code == 404


async def test_delete_user_requires_admin(client, user_token, admin):
    resp = await client.delete(
        f"/users/{admin.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


async def test_delete_user_cannot_delete_self(client, admin_token, admin):
    resp = await client.delete(
        f"/users/{admin.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
