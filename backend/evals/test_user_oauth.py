import os
import sys
import time
import sqlite3
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock

# Ensure backend root is in pythonpath
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from engine.db import (
    init_db,
    DB_PATH,
    save_user_oauth_token,
    get_user_oauth_token,
    delete_user_oauth_token,
    is_user_oauth_connected,
    save_oauth_state,
    consume_oauth_state
)
from engine.vault import decrypt_data
from app.core.email_tool import (
    load_gmail_credentials,
    get_gmail_service,
    get_vocalis_app_credentials
)
from app.core.calendar_tool import get_calendar_service


@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    try:
        with sqlite3.connect(DB_PATH, timeout=15.0) as con:
            con.execute("DELETE FROM user_oauth_tokens")
            con.execute("DELETE FROM oauth_states")
            con.execute("DELETE FROM sessions")
            con.execute("DELETE FROM users")
            con.commit()
    except Exception:
        pass


@pytest.mark.asyncio
async def test_get_google_auth_url_and_csrf_state_persistence():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Signup user
        signup_resp = await client.post(
            "/api/auth/signup",
            json={"email": "alice@vocalis.ai", "password": "Password123!", "display_name": "Alice"}
        )
        token = signup_resp.json()["token"]
        user_id = signup_resp.json()["user"]["id"]

        with patch("app.core.email_tool.get_vocalis_app_credentials", return_value=("fake_client_id_123", "fake_secret_456")):
            resp = await client.get("/api/auth/google/url", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "accounts.google.com" in data["auth_url"]
            assert "fake_client_id_123" in data["auth_url"]
            assert "state=" in data["auth_url"]

            # Inspect database to confirm state was persisted bound to user_id
            with sqlite3.connect(DB_PATH, timeout=15.0) as con:
                cursor = con.cursor()
                cursor.execute("SELECT state, user_id, expires_at FROM oauth_states WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                assert row is not None
                state_db, uid_db, exp_db = row
                assert uid_db == user_id
                assert exp_db > time.time()


@pytest.mark.asyncio
async def test_oauth_callback_csrf_one_time_consumption():
    # Save a test state
    state = "secure_state_xyz_123"
    save_oauth_state(state=state, user_id=42, expires_at=time.time() + 300)

    # First consumption: succeeds and returns user_id
    consumed_uid = consume_oauth_state(state)
    assert consumed_uid == 42

    # Second consumption (replay attack): fails and returns None
    replay_uid = consume_oauth_state(state)
    assert replay_uid is None


@pytest.mark.asyncio
async def test_oauth_callback_stores_fernet_encrypted_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create user
        signup_resp = await client.post(
            "/api/auth/signup",
            json={"email": "bob@vocalis.ai", "password": "Password123!", "display_name": "Bob"}
        )
        user_id = signup_resp.json()["user"]["id"]

        # Setup state
        state = "state_bob_999"
        save_oauth_state(state=state, user_id=user_id, expires_at=time.time() + 300)

        with patch("app.core.email_tool.get_vocalis_app_credentials", return_value=("app_id", "app_secret")), \
             patch("app.api.routes_auth.exchange_google_oauth_code", return_value=("1//04_SECRET_REFRESH_TOKEN_BOB", "bob.personal@gmail.com")):

            cb_resp = await client.get(f"/api/auth/google/callback?code=mock_auth_code&state={state}")
            assert cb_resp.status_code == 200
            assert "Google Account Connected!" in cb_resp.text
            assert "bob.personal@gmail.com" in cb_resp.text

        # Directly inspect SQLite table user_oauth_tokens to ensure encryption at rest
        with sqlite3.connect(DB_PATH, timeout=15.0) as con:
            cursor = con.cursor()
            cursor.execute("SELECT refresh_token_enc, google_email FROM user_oauth_tokens WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            assert row is not None
            raw_enc_token, g_email = row
            # Assert Fernet tag prefix
            assert raw_enc_token.startswith("enc::")
            # Assert plaintext is NOT stored
            assert "1//04_SECRET_REFRESH_TOKEN_BOB" not in raw_enc_token
            # Assert decryption succeeds
            decrypted = decrypt_data(raw_enc_token)
            assert decrypted == "1//04_SECRET_REFRESH_TOKEN_BOB"
            assert g_email == "bob.personal@gmail.com"


def test_per_user_isolation_and_no_silent_fallback():
    """
    CRITICAL: Verifies that an authenticated user who has NOT connected Google
    NEVER silently falls back to the host machine's global token.
    """
    init_db()

    # User 1 has connected Google
    save_user_oauth_token(
        user_id=101,
        refresh_token="1//USER1_TOKEN",
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        google_email="user1@gmail.com"
    )

    # User 2 has NOT connected Google (no row in user_oauth_tokens)

    with patch("app.core.email_tool.get_vocalis_app_credentials", return_value=("app_cid", "app_csec")):
        # User 1 loads their own credentials
        creds1 = load_gmail_credentials(user_id=101)
        assert creds1 is not None
        assert creds1.refresh_token == "1//USER1_TOKEN"

        # User 2 loads credentials -> STRICT NONE (NO silent fallback)
        creds2 = load_gmail_credentials(user_id=102)
        assert creds2 is None

        # Calling get_gmail_service for User 2 raises clean human error
        with pytest.raises(RuntimeError) as exc_info:
            get_gmail_service(user_id=102)
        assert "Google Account not connected" in str(exc_info.value)

        # Calling get_calendar_service for User 2 raises clean human error
        with pytest.raises(RuntimeError) as exc_info_cal:
            get_calendar_service(user_id=102)
        assert "Google Account not connected" in str(exc_info_cal.value)


@pytest.mark.asyncio
async def test_google_oauth_status_and_disconnect():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Signup
        signup_resp = await client.post(
            "/api/auth/signup",
            json={"email": "carol@vocalis.ai", "password": "Password123!", "display_name": "Carol"}
        )
        token = signup_resp.json()["token"]
        user_id = signup_resp.json()["user"]["id"]

        # Initial status: not connected
        st1 = await client.get("/api/auth/google/status", headers={"Authorization": f"Bearer {token}"})
        assert st1.status_code == 200
        assert st1.json()["is_connected"] is False

        # Connect user
        save_user_oauth_token(
            user_id=user_id,
            refresh_token="1//CAROL_REFRESH",
            scopes=["https://www.googleapis.com/auth/gmail.send"],
            google_email="carol@gmail.com"
        )

        # Status after connection: connected
        st2 = await client.get("/api/auth/google/status", headers={"Authorization": f"Bearer {token}"})
        assert st2.status_code == 200
        assert st2.json()["is_connected"] is True
        assert st2.json()["google_email"] == "carol@gmail.com"

        # Disconnect
        disc_resp = await client.post("/api/auth/google/disconnect", headers={"Authorization": f"Bearer {token}"})
        assert disc_resp.status_code == 200

        # Status after disconnect: not connected
        st3 = await client.get("/api/auth/google/status", headers={"Authorization": f"Bearer {token}"})
        assert st3.status_code == 200
        assert st3.json()["is_connected"] is False
