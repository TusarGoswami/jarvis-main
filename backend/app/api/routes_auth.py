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
