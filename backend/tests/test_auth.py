from tests.conftest import register


def test_register_returns_token_and_me_works(client):
    headers = register(client, "ada@example.com", "Ada Obi")
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "ada@example.com"
    assert body["full_name"] == "Ada Obi"


def test_register_duplicate_email_conflicts(client):
    register(client, "ada@example.com")
    resp = client.post(
        "/auth/register",
        json={
            "email": "ada@example.com",
            "password": "password123",
            "full_name": "Someone Else",
        },
    )
    assert resp.status_code == 409


def test_register_normalizes_email_case(client):
    register(client, "Ada@Example.com")
    resp = client.post(
        "/auth/login", json={"email": "ada@example.com", "password": "password123"}
    )
    assert resp.status_code == 200


def test_login_ok(client):
    register(client, "ada@example.com")
    resp = client.post(
        "/auth/login", json={"email": "ada@example.com", "password": "password123"}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_wrong_password_unauthorized(client):
    register(client, "ada@example.com")
    resp = client.post(
        "/auth/login", json={"email": "ada@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401


def test_me_with_bad_token_unauthorized(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_register_validation(client):
    resp = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "password123", "full_name": "X"},
    )
    assert resp.status_code == 422

    resp = client.post(
        "/auth/register",
        json={"email": "ok@example.com", "password": "short", "full_name": "X"},
    )
    assert resp.status_code == 422
