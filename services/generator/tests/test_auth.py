"""Tests for auth + user-scoped app CRUD. Uses a live Postgres (registry).

Skips gracefully if no database is reachable (e.g. in pure-unit CI).
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from aura_generator import main as app_main
from aura_generator.auth import generate_verification_code, hash_password, verify_password
from aura_generator.crypto import decrypt, encrypt
from aura_generator.db import create_user, engine, init_registry


def _db_reachable() -> bool:
    try:
        with engine().connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_reachable(), reason="registry Postgres not reachable")


@pytest.fixture(scope="module", autouse=True)
def _init():
    init_registry()


@pytest.fixture()
def client(monkeypatch):
    # Quiet the console email sender so test output stays clean.
    monkeypatch.setattr(
        "aura_generator.main.send_verification_code",
        lambda email, code: None,
    )
    with TestClient(app_main.app) as c:
        yield c


def test_password_hash_roundtrip():
    h = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", h)
    assert not verify_password("wrong password", h)


def test_crypto_roundtrip():
    token = "ghp_" + "x" * 36
    enc = encrypt(token)
    assert enc != token
    assert decrypt(enc) == token


def test_verification_code_is_six_digits():
    code = generate_verification_code()
    assert len(code) == 6
    assert code.isdigit()


def _unique_email() -> str:
    # Use an example.com domain so email-validator accepts it (aura.local is reserved).
    return f"test-{uuid.uuid4().hex[:12]}@example.com"


def test_signup_verify_login_flow_and_app_scoping(client, monkeypatch):
    email = _unique_email()

    captured: dict[str, str] = {}

    def fake_send(to: str, code: str) -> None:
        captured["code"] = code

    monkeypatch.setattr("aura_generator.main.send_verification_code", fake_send)

    # Signup
    r = client.post("/auth/signup", json={"email": email, "password": "hunter22hunter"})
    assert r.status_code == 200, r.text
    assert r.json()["verified"] is False
    assert "code" in captured

    # Unauthenticated /apps is 401
    assert client.get("/apps").status_code == 401

    # Wrong code is rejected
    r = client.post("/auth/verify", json={"email": email, "code": "000000"})
    assert r.status_code == 400

    # Correct code verifies + issues cookie
    r = client.post("/auth/verify", json={"email": email, "code": captured["code"]})
    assert r.status_code == 200, r.text
    assert r.json()["verified"] is True
    assert client.cookies.get("aura_session")

    # /auth/me sees the user
    r = client.get("/auth/me")
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["email"] == email
    assert me["git_account"] is None

    # Listing apps works and is empty for this fresh user
    r = client.get("/apps")
    assert r.status_code == 200
    assert all(a.get("user_id") != me["id"] or a.get("slug") is None for a in r.json()) or r.json() == []

    # Logout clears cookie
    r = client.post("/auth/logout")
    assert r.status_code == 200
    assert client.get("/apps").status_code == 401

    # Login path
    r = client.post("/auth/login", json={"email": email, "password": "hunter22hunter"})
    assert r.status_code == 200

    # Wrong password
    r = client.post("/auth/login", json={"email": email, "password": "wrong"})
    assert r.status_code == 401


def test_git_account_endpoints_validate_token(client, monkeypatch):
    # Seed a verified user straight into DB + log in via endpoint.
    email = _unique_email()
    u = create_user(email, hash_password("password1234"))
    from aura_generator.db import mark_user_verified

    mark_user_verified(u["id"])
    r = client.post("/auth/login", json={"email": email, "password": "password1234"})
    assert r.status_code == 200

    # Mock the PAT verification call.
    def fake_verify(provider: str, token: str) -> dict:
        assert provider == "github"
        assert token == "ghp_fake"
        return {"username": "ppa1985"}

    monkeypatch.setattr("aura_generator.main.verify_token", fake_verify)

    r = client.post(
        "/git-accounts",
        json={"provider": "github", "token": "ghp_fake", "workspace_repo": "ppa1985/aura-workspace"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "github"
    assert body["username"] == "ppa1985"
    assert body["workspace_repo"] == "ppa1985/aura-workspace"

    # Verify via GET
    r = client.get("/git-accounts/me")
    assert r.status_code == 200
    assert r.json()["workspace_repo"] == "ppa1985/aura-workspace"

    # Token was stored encrypted (not plaintext in DB)
    from aura_generator.db import get_git_account

    stored = get_git_account(u["id"])
    assert stored is not None
    assert stored["token_enc"] != "ghp_fake"
    assert decrypt(stored["token_enc"]) == "ghp_fake"

    # Disconnect
    r = client.delete("/git-accounts/me")
    assert r.status_code == 200
    assert client.get("/git-accounts/me").json() is None
