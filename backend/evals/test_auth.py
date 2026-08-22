import os
import sys
import time
import sqlite3
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

# Ensure backend root is in pythonpath
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from engine.db import init_db, DB_PATH, create_session, get_user_by_email
from app.core.auth import hash_password, verify_password, _login_failures


@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    _login_failures.clear()
    try:
        with sqlite3.connect(DB_PATH, timeout=15.0) as con:
            con.execute("DELETE FROM sessions")
            con.execute("DELETE FROM users")
            con.commit()
    except Exception:
        pass


@pytest.mark.asyncio
async def test_signup_success_and_cookie_generation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/signup",
            json={
                "email": "alice@vocalis.ai",
                "password": "Password123!",
                "display_name": "Alice Wonderland"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["user"]["email"] == "alice@vocalis.ai"
        assert data["user"]["display_name"] == "Alice Wonderland"
        assert "token" in data
        assert "session_token" in resp.cookies


@pytest.mark.asyncio
async def test_signup_duplicate_email_rejection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First signup
        await client.post(
            "/api/auth/signup",
            json={"email": "bob@vocalis.ai", "password": "Password123!"}
        )
        # Second signup with same email
        dup_resp = await client.post(
            "/api/auth/signup",
            json={"email": "bob@vocalis.ai", "password": "Password123!"}
        )
        assert dup_resp.status_code == 400
        assert "already exists" in dup_resp.json()["detail"]


@pytest.mark.asyncio
async def test_signup_weak_password_rejection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/signup",
            json={"email": "short@vocalis.ai", "password": "short"}
        )
        assert resp.status_code == 400
        assert "at least 8 characters" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Signup first
        await client.post(
            "/api/auth/signup",
            json={"email": "carol@vocalis.ai", "password": "SecurePassword99"}
        )

        # Login
        login_resp = await client.post(
            "/api/auth/login",
            json={"email": "carol@vocalis.ai", "password": "SecurePassword99"}
        )
        assert login_resp.status_code == 200
        data = login_resp.json()
        assert data["status"] == "success"
        assert data["user"]["email"] == "carol@vocalis.ai"
        assert "token" in data
        assert "session_token" in login_resp.cookies


@pytest.mark.asyncio
async def test_login_generic_error_on_wrong_password_and_nonexistent_email():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create user
        await client.post(
            "/api/auth/signup",
            json={"email": "dave@vocalis.ai", "password": "RealPassword123"}
        )

        # 1. Wrong password
        wrong_pw_resp = await client.post(
            "/api/auth/login",
            json={"email": "dave@vocalis.ai", "password": "WRONG_PASSWORD"}
        )
        assert wrong_pw_resp.status_code == 401
        err1 = wrong_pw_resp.json()["detail"]

        # 2. Nonexistent email
        no_email_resp = await client.post(
            "/api/auth/login",
            json={"email": "ghost@vocalis.ai", "password": "RealPassword123"}
        )
        assert no_email_resp.status_code == 401
        err2 = no_email_resp.json()["detail"]

        # Assert exact same generic message (prevents user enumeration)
        assert err1 == "Invalid email or password."
        assert err2 == "Invalid email or password."


@pytest.mark.asyncio
async def test_protected_me_endpoint_and_revocable_logout():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Signup
        signup_resp = await client.post(
            "/api/auth/signup",
            json={"email": "eve@vocalis.ai", "password": "StrongPassword123", "display_name": "Eve"}
        )
        token = signup_resp.json()["token"]

        # Access /api/auth/me with Bearer header
        me_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["user"]["email"] == "eve@vocalis.ai"

        # Logout
        logout_resp = await client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert logout_resp.status_code == 200

        # Access /api/auth/me after logout -> 401 Unauthorized
        me_after = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_after.status_code == 401


@pytest.mark.asyncio
async def test_expired_session_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        signup_resp = await client.post(
            "/api/auth/signup",
            json={"email": "frank@vocalis.ai", "password": "StrongPassword123"}
        )
        user_id = signup_resp.json()["user"]["id"]

        # Insert expired token manually
        expired_tok = "tok_expired_999"
        create_session(user_id=user_id, token=expired_tok, expires_at=time.time() - 100)

        # Access with expired token -> 401
        resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_tok}"})
        assert resp.status_code == 401


def test_password_hashing_direct_db_inspection():
    """
    Directly queries SQLite to ensure plaintext passwords never touch the DB.
    """
    init_db()
    pw_plain = "SuperSecretPlainText123!"
    pw_hash = hash_password(pw_plain)

    con = sqlite3.connect(DB_PATH)
    cursor = con.cursor()
    cursor.execute(
        "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
        ("inspector@vocalis.ai", pw_hash, "Inspector")
    )
    con.commit()

    cursor.execute("SELECT password_hash FROM users WHERE email = 'inspector@vocalis.ai'")
    row = cursor.fetchone()
    con.close()

    stored_hash = row[0]
    # Assert bcrypt prefix format
    assert stored_hash.startswith("$2b$")
    # Assert plaintext is not anywhere in stored hash
    assert pw_plain not in stored_hash
    # Assert hash verification succeeds
    assert verify_password(pw_plain, stored_hash) is True
    assert verify_password("WrongPassword!", stored_hash) is False


@pytest.mark.asyncio
async def test_login_rate_limiting():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create user
        await client.post(
            "/api/auth/signup",
            json={"email": "target@vocalis.ai", "password": "CorrectPassword123"}
        )

        # Fail 5 times
        for _ in range(5):
            fail_resp = await client.post(
                "/api/auth/login",
                json={"email": "target@vocalis.ai", "password": "BadPassword"}
            )
            assert fail_resp.status_code == 401

        # 6th attempt should be blocked by rate limiter (HTTP 429)
        blocked_resp = await client.post(
            "/api/auth/login",
            json={"email": "target@vocalis.ai", "password": "CorrectPassword123"}
        )
        assert blocked_resp.status_code == 429
        assert "Too many failed login attempts" in blocked_resp.json()["detail"]
