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
