import time
import secrets
import bcrypt
from typing import Optional, Dict, Any, Tuple
from fastapi import Request, Header, HTTPException, Depends

from engine.db import get_session_user, create_session, delete_session


# Password Hashing & Verification
def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using bcrypt with salt rounds=12.
    """
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a bcrypt hash.
    """
    try:
        if not plain_password or not hashed_password:
            return False
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def generate_session_token() -> str:
    """
    Generates a cryptographically secure random session token.
    """
    return secrets.token_urlsafe(32)


# IP & Reverse Proxy Helper
def get_client_ip(request: Request) -> str:
    """
    Extracts the real client IP address, handling X-Forwarded-For if behind a reverse proxy/load balancer.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First IP in the comma-separated chain is the client
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


# In-Memory Rate Limiter for Login Attempts
# Structure: { key: [(timestamp), (timestamp), ...] }
_login_failures: Dict[str, list] = {}
RATE_LIMIT_WINDOW_SECONDS = 900  # 15 minutes
MAX_FAILED_ATTEMPTS = 5


def check_login_rate_limit(client_ip: str, email: str) -> bool:
    """
    Checks if login attempts for this IP or email have exceeded the threshold.
    Returns True if allowed, False if rate limited.
    """
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS

    for key in [f"ip:{client_ip}", f"email:{email.strip().lower()}"]:
        if key in _login_failures:
            # Purge expired timestamps
            _login_failures[key] = [t for t in _login_failures[key] if t > cutoff]
            if len(_login_failures[key]) >= MAX_FAILED_ATTEMPTS:
                return False
    return True


def record_login_attempt(client_ip: str, email: str, success: bool):
    """
    Records a login attempt. Clears history on success, appends timestamp on failure.
    """
    now = time.time()
    ip_key = f"ip:{client_ip}"
    email_key = f"email:{email.strip().lower()}"

    if success:
        _login_failures.pop(ip_key, None)
        _login_failures.pop(email_key, None)
    else:
        _login_failures.setdefault(ip_key, []).append(now)
        _login_failures.setdefault(email_key, []).append(now)


# Generalized User Authentication Dependency
async def verify_user_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_auth_token: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    FastAPI dependency that validates session authentication.
    Checks:
    1. Explicit 'Authorization: Bearer <token>' header
    2. 'x-auth-token' header
    3. httpOnly cookie 'session_token'
    Returns the authenticated user dict or raises HTTP 401.
    """
    token = None

    # 1. Bearer header check (prioritize explicit token if provided)
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif x_auth_token:
        token = x_auth_token.strip()
    elif "session_token" in request.cookies:
        token = request.cookies.get("session_token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please sign in."
        )

    user = get_session_user(token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session token. Please sign in again."
        )

    # Attach token to user object for reference
    user["current_session_token"] = token
    return user
