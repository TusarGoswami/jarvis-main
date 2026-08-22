import re
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from engine.db import create_user, get_user_by_email, create_session, delete_session
from app.core.auth import (
    hash_password,
    verify_password,
    generate_session_token,
    get_client_ip,
    check_login_rate_limit,
    record_login_attempt,
    verify_user_auth
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

SESSION_TTL_SECONDS = 7 * 86400  # 7 Days


class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


EMAIL_REGEX = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')


@router.post("/signup")
async def signup(req: SignupRequest, request: Request, response: Response):
    """
    Registers a new user account and creates an authenticated session.
    """
    email_clean = req.email.strip().lower()
    if not EMAIL_REGEX.match(email_clean):
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")

    if not req.password or len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")

    try:
        pw_hash = hash_password(req.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    user_id = create_user(
        email=email_clean,
        password_hash=pw_hash,
        display_name=req.display_name
    )

    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists. Please log in."
        )

    # Issue 7-day session token
    token = generate_session_token()
    expires_at = time.time() + SESSION_TTL_SECONDS
    create_session(user_id=user_id, token=token, expires_at=expires_at)

    # Set httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=SESSION_TTL_SECONDS,
        path="/"
    )

    display_name = req.display_name.strip() if req.display_name else email_clean.split('@')[0]
    return {
        "status": "success",
        "message": "Account created successfully.",
        "user": {
            "id": user_id,
            "email": email_clean,
            "display_name": display_name
        },
        "token": token
    }


@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response):
    """
    Authenticates a user and issues a revocable session token.
    """
    email_clean = req.email.strip().lower()
    client_ip = get_client_ip(request)

    # Rate limiting check
    if not check_login_rate_limit(client_ip, email_clean):
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Please wait 15 minutes before trying again."
        )

    user = get_user_by_email(email_clean)
    if not user or not verify_password(req.password, user["password_hash"]):
        record_login_attempt(client_ip, email_clean, success=False)
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    # Success: record attempt, clear failure counters
    record_login_attempt(client_ip, email_clean, success=True)

    # Issue 7-day session token
    token = generate_session_token()
    expires_at = time.time() + SESSION_TTL_SECONDS
    create_session(user_id=user["id"], token=token, expires_at=expires_at)

    # Set httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=SESSION_TTL_SECONDS,
        path="/"
    )

    return {
        "status": "success",
        "message": "Signed in successfully.",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"]
        },
        "token": token
    }


@router.post("/logout")
async def logout(request: Request, response: Response):
    """
    Revokes the current session token server-side and clears the cookie.
    """
    # Try getting token from cookie or header
    token = request.cookies.get("session_token")
    auth_header = request.headers.get("authorization")
    if not token and auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    if token:
        delete_session(token)

    response.delete_cookie(key="session_token", path="/")
    return {
        "status": "success",
        "message": "Logged out successfully."
    }


@router.get("/me")
async def get_current_user_profile(user: Dict[str, Any] = Depends(verify_user_auth)):
    """
    Protected endpoint: returns the authenticated user's profile.
    """
    return {
        "status": "success",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"],
            "created_at": user.get("created_at")
        }
    }


# ==================== PER-USER GOOGLE OAUTH FLOW ====================

GOOGLE_SCOPES_LIST = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.email"
]

GOOGLE_AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google/url")
async def get_google_auth_url(request: Request, user: Dict[str, Any] = Depends(verify_user_auth)):
    """
    Generates a Google OAuth consent URL with a persistent CSRF state token bound to the user.
    """
    from urllib.parse import urlencode
    import secrets
    from app.core.email_tool import get_vocalis_app_credentials
    from engine.db import save_oauth_state

    client_id, client_secret = get_vocalis_app_credentials()
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="Vocalis AI Google OAuth application credentials not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        )

    # Generate cryptographically secure one-time CSRF state token (10 min TTL)
    state = secrets.token_urlsafe(32)
    save_oauth_state(state=state, user_id=user["id"], expires_at=time.time() + 600)

    # Determine callback redirect URI
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/auth/google/callback"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES_LIST),
        "access_type": "offline",
        "prompt": "consent",
        "state": state
    }
    auth_url = f"{GOOGLE_AUTH_BASE}?{urlencode(params)}"
    return {
        "status": "success",
        "auth_url": auth_url
    }


async def exchange_google_oauth_code(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str
) -> tuple[Optional[str], Optional[str]]:
    """
    Exchanges authorization code with Google OAuth server.
    Returns (refresh_token, google_email).
    """
    import httpx
    async with httpx.AsyncClient(timeout=15.0) as http_client:
        token_resp = await http_client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
        )

        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to exchange authorization code: {token_resp.text}")

        token_data = token_resp.json()
        refresh_token = token_data.get("refresh_token")
        access_token = token_data.get("access_token")

        google_email = None
        if access_token:
            try:
                userinfo_resp = await http_client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if userinfo_resp.status_code == 200:
                    google_email = userinfo_resp.json().get("email")
            except Exception:
                pass

    return refresh_token, google_email


@router.get("/google/callback")
async def google_oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    """
    Handles the Google OAuth 2.0 authorization code callback.
    Validates CSRF state, exchanges code for refresh token, and encrypts into user_oauth_tokens.
    """
    from fastapi.responses import HTMLResponse
    from engine.db import consume_oauth_state, save_user_oauth_token
    from app.core.email_tool import get_vocalis_app_credentials

    if error:
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
              <body style="background:#030712;color:#ef4444;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;">
                <h2>Google Authorization Cancelled or Failed</h2>
                <p style="color:#94a3b8;">Error: {error}</p>
                <script>setTimeout(() => window.close(), 3000);</script>
              </body>
            </html>
            """,
            status_code=400
        )

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing authorization code or state parameter.")

    # 1. Validate and consume one-time CSRF state token
    user_id = consume_oauth_state(state)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state parameter. Please try connecting again.")

    client_id, client_secret = get_vocalis_app_credentials()
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Vocalis Google OAuth app credentials not found.")

    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/auth/google/callback"

    # 2. Exchange code for tokens
    refresh_token, google_email = await exchange_google_oauth_code(
        code=code,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri
    )

    if not refresh_token:
        raise HTTPException(
            status_code=400,
            detail="Google did not return a refresh token. Please revoke Vocalis access in your Google Account security settings and reconnect with consent prompt."
        )

    # 3. Save encrypted refresh token in user_oauth_tokens table
    save_user_oauth_token(
        user_id=user_id,
        refresh_token=refresh_token,
        scopes=GOOGLE_SCOPES_LIST,
        google_email=google_email
    )

    email_display = google_email or "Connected Account"
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
          <head>
            <title>Google Account Connected</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="background:#030712;color:#22d3ee;font-family:ui-sans-serif,system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;margin:0;">
            <div style="background:rgba(15,23,42,0.9);border:1px solid rgba(6,182,212,0.4);border-radius:16px;padding:32px;text-align:center;box-shadow:0 0 30px rgba(6,182,212,0.2);max-width:400px;width:90%;">
              <div style="font-size:32px;margin-bottom:12px;">✅</div>
              <h2 style="margin:0 0 8px 0;color:#f8fafc;font-size:18px;">Google Account Connected!</h2>
              <p style="color:#94a3b8;font-size:14px;margin:0 0 20px 0;">{email_display}</p>
              <p style="color:#64748b;font-size:12px;margin:0;">You can close this window now.</p>
            </div>
            <script>
              if (window.opener) {{
                window.opener.postMessage({{ type: 'VOCALIS_GOOGLE_AUTH_SUCCESS', email: '{email_display}' }}, '*');
                setTimeout(() => window.close(), 1200);
              }} else {{
                setTimeout(() => {{ window.location.href = 'http://localhost:3000'; }}, 1500);
              }}
            </script>
          </body>
        </html>
        """
    )


@router.get("/google/status")
async def get_google_auth_status(user: Dict[str, Any] = Depends(verify_user_auth)):
    """
    Returns whether the authenticated user has connected their Google account.
    """
    from engine.db import is_user_oauth_connected
    connected, email = is_user_oauth_connected(user["id"])
    return {
        "status": "success",
        "is_connected": connected,
        "google_email": email
    }


@router.post("/google/disconnect")
async def disconnect_google_auth(user: Dict[str, Any] = Depends(verify_user_auth)):
    """
    Disconnects and deletes the user's Google OAuth credentials.
    """
    from engine.db import delete_user_oauth_token
    delete_user_oauth_token(user["id"])
    return {
        "status": "success",
        "message": "Google account disconnected successfully."
    }
