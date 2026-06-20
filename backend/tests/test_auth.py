"""Auth round-trip tests (register -> login -> me)."""

from __future__ import annotations

import uuid

API = "/api/v1"


def _unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:10]}@example.com"


def test_register_login_me_flow(client, db_required):
    email = _unique_email()
    password = "password123"

    res = client.post(f"{API}/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    assert res.json()["email"] == email

    res = client.post(f"{API}/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200, res.text
    tokens = res.json()
    assert tokens["token_type"] == "bearer"

    auth_header = {"Authorization": f"Bearer {tokens['access_token']}"}
    res = client.get(f"{API}/auth/me", headers=auth_header)
    assert res.status_code == 200
    assert res.json()["email"] == email


def test_duplicate_registration_conflicts(client, db_required):
    email = _unique_email()
    payload = {"email": email, "password": "password123"}
    assert client.post(f"{API}/auth/register", json=payload).status_code == 201
    assert client.post(f"{API}/auth/register", json=payload).status_code == 409


def test_wrong_password_rejected(client, db_required):
    email = _unique_email()
    client.post(f"{API}/auth/register", json={"email": email, "password": "password123"})
    res = client.post(f"{API}/auth/login", data={"username": email, "password": "wrong"})
    assert res.status_code == 401


def test_me_requires_auth(client):
    assert client.get(f"{API}/auth/me").status_code == 401
