import os
import re
import json
import base64
import time
from email.mime.text import MIMEText
from typing import Dict, Any, Optional, List
from collections import deque

from engine.vault import encrypt_data, decrypt_data
from app.core.sanitizer import sanitize_text

# Gmail OAuth Scope - strictly limited to sending emails
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Path to encrypted Gmail token storage
_JARVIS_DIR = os.path.join(os.path.expanduser("~"), ".jarvis")
os.makedirs(_JARVIS_DIR, exist_ok=True)
GMAIL_TOKEN_PATH = os.path.join(_JARVIS_DIR, "gmail_token.json")

# Standard RFC 5322 compatible email pattern
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

class EmailRateLimiter:
    """
    Sliding-window rate limiter for email dispatching.
    Prevents runaway loops, bad prompts, or spam.
    """
    def __init__(self, max_per_minute: int = 5, max_per_hour: int = 30):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self._minute_timestamps: deque = deque()
        self._hour_timestamps: deque = deque()

    def can_send(self) -> tuple[bool, Optional[str]]:
        now = time.time()
        # Evict timestamps older than 60s
        while self._minute_timestamps and now - self._minute_timestamps[0] > 60:
            self._minute_timestamps.popleft()
        # Evict timestamps older than 3600s
        while self._hour_timestamps and now - self._hour_timestamps[0] > 3600:
            self._hour_timestamps.popleft()

        if len(self._minute_timestamps) >= self.max_per_minute:
            return False, f"Email rate limit exceeded (max {self.max_per_minute} emails/minute). Please wait."
        if len(self._hour_timestamps) >= self.max_per_hour:
            return False, f"Email hourly limit exceeded (max {self.max_per_hour} emails/hour). Please wait."

        return True, None

    def record_send(self):
        now = time.time()
        self._minute_timestamps.append(now)
        self._hour_timestamps.append(now)

    def reset(self):
        self._minute_timestamps.clear()
        self._hour_timestamps.clear()

email_rate_limiter = EmailRateLimiter(max_per_minute=5, max_per_hour=30)


def validate_email_format(email: str) -> bool:
    """
    Validates recipient email address format against standard RFC pattern.
    Supports single email address or comma/semicolon/and-separated list of addresses.
    """
    if not email or not isinstance(email, str):
        return False
    parts = [p.strip() for p in re.split(r'[,;\s]+', email.strip()) if p.strip() and p.strip().lower() != "and"]
    if not parts:
        return False
    return all(bool(EMAIL_REGEX.match(p)) for p in parts)


def auto_generate_subject(body: str) -> str:
    """
    Generates a concise subject if none is provided.
    Extracts up to the first 5-6 words or creates a meaningful summary title.
    """
    clean_body = re.sub(r'[\r\n]+', ' ', body).strip()
    # Remove leading quotes or punctuation
    clean_body = clean_body.strip('"\'`')
    if not clean_body:
        return "Message from Vocalis AI"

    words = clean_body.split()
    if len(words) <= 6:
        subject = clean_body
    else:
        subject = " ".join(words[:6]) + "..."

    # Capitalize first letter
    return subject[0].upper() + subject[1:] if subject else "Message from Vocalis AI"


def parse_email_command(text: str) -> Dict[str, Optional[str]]:
    """
    Extracts `to` (single or multiple comma-separated recipients), `subject`, and `body`
    from natural language email instructions.
    
    Examples handled:
    - 'Send a mail to hridayeshdebsarma@gmail.com saying honesty is the best policy'
    - 'Send a mail to hridayeshdebsarma6@gmail.com and tusargoswami0027@gmail.com and adarshyadav3924@gmail.com saying honesty is the best policy'
    - 'Email john@example.com with subject "Meeting notes" and tell him the meeting is moved to 3pm'
    - 'Send an email to sarah@company.com: the report is attached, let me know if you have questions'
    """
    q = text.strip()

    recipient: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None

    # 1. Extract all explicit email addresses present
    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', q)
    if emails:
        seen = set()
        unique_emails = []
        for e in emails:
            if e.lower() not in seen:
                seen.add(e.lower())
                unique_emails.append(e)
        recipient = ", ".join(unique_emails)

    # 2. Check for explicit subject patterns:
    # e.g., with subject 'Meeting notes' / with subject "Meeting notes" / subject: Meeting notes
    subj_match = re.search(
        r'(?:with\s+subject|subjected?|having\s+subject)\s*[:=]?\s*[\'"]([^\'"]+)[\'"]',
        q,
        re.IGNORECASE
    )
    if not subj_match:
        subj_match = re.search(
            r'(?:with\s+subject|subjected?|having\s+subject)\s*[:=]?\s*([^,\n]+?)(?:\s+(?:and\s+(?:tell|saying|say|body)|body:|message:|$))',
            q,
            re.IGNORECASE
        )
    if subj_match:
        subject = subj_match.group(1).strip()

    # 3. Extract body
    # Pattern A: saying <body text>
    saying_match = re.search(r'\bsaying\s+(.+)$', q, re.IGNORECASE | re.DOTALL)
    if saying_match:
        body = saying_match.group(1).strip()
    # Pattern B: and tell (him/her/them/user)? <body text>
    if not body:
        tell_match = re.search(r'\b(?:and\s+)?tell\s+(?:him|her|them|user)?\s*(?:that|to)?\s*(.+)$', q, re.IGNORECASE | re.DOTALL)
        if tell_match:
            body = tell_match.group(1).strip()
    # Pattern C: colon separator after recipient e.g., "to sarah@company.com: the report is attached..."
    if not body:
        colon_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\s*[:\-]\s*(.+)$', q, re.IGNORECASE | re.DOTALL)
        if colon_match:
            body = colon_match.group(1).strip()
    # Pattern D: message/body: <body text>
    if not body:
        msg_match = re.search(r'\b(?:message|body|content|text)\s*[:=]\s*(.+)$', q, re.IGNORECASE | re.DOTALL)
        if msg_match:
            body = msg_match.group(1).strip()
    # Pattern E: "send <body text> to <recipient>"
    if not body:
        to_end_match = re.search(r'^(?:send|draft|dispatch)\s+(?:a\s+)?(?:mail|email|message)\s+(.+?)\s+to\s+[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', q, re.IGNORECASE | re.DOTALL)
        if to_end_match:
            body = to_end_match.group(1).strip()

    # Clean up quotes from extracted body
    if body:
        body = body.strip(' "\'`')

    # If body was not found but text remains after recipient
    if not body and emails:
        last_email = emails[-1]
        after_recipient = q.split(last_email, 1)[-1].strip()
        # Clean leading words like "and", "that", ":", "-"
        after_recipient = re.sub(r'^(?:and|that|to|with|saying|tell\s+him|tell\s+her|:|-)\s*', '', after_recipient, flags=re.I).strip()
        if after_recipient:
            body = after_recipient.strip(' "\'`')

    # If no subject was found, generate automatically from body
    if not subject and body:
        subject = auto_generate_subject(body)
    elif not subject:
        subject = "Message from Vocalis AI"

    return {
        "to": recipient,
        "subject": subject,
        "body": body
    }


def format_email_confirmation_reason(to: str, subject: str, body: str) -> str:
    """
    Builds the standardized confirmation prompt for guardrails and the Activity Feed.
    """
    body_display = f'"{body}"' if body else '""'
    return (
        f"CONFIRM ACTION: Send Email\n"
        f"To: {to}\n"
        f"Subject: {subject}\n"
        f"Body: {body_display}"
    )


DEFAULT_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly"
]


def save_gmail_credentials(
    refresh_token: str,
    client_id: str,
    client_secret: str,
    token_path: Optional[str] = None,
    scopes: Optional[List[str]] = None
) -> str:
    """
    Encrypts and saves Gmail & Calendar OAuth credentials to the secure token file at rest.
    """
    target_path = token_path or GMAIL_TOKEN_PATH
    payload = {
        "refresh_token": encrypt_data(refresh_token),
        "client_id": encrypt_data(client_id),
        "client_secret": encrypt_data(client_secret),
        "token_uri": "https://oauth2.googleapis.com/token",
        "scopes": scopes or DEFAULT_GOOGLE_SCOPES
    }
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return target_path


def load_gmail_credentials(token_path: Optional[str] = None) -> Optional[Any]:
    """
    Loads and decrypts Gmail & Calendar OAuth credentials from storage, creating
    a valid Google Credentials object for automatic token refreshing.
    """
    target_path = token_path or GMAIL_TOKEN_PATH
    if not os.path.exists(target_path):
        return None

    try:
        from google.oauth2.credentials import Credentials
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_refresh = data.get("refresh_token")
        raw_client_id = data.get("client_id")
        raw_client_secret = data.get("client_secret")

        refresh_token = decrypt_data(raw_refresh)
        client_id = decrypt_data(raw_client_id)
        client_secret = decrypt_data(raw_client_secret)
        token_uri = data.get("token_uri", "https://oauth2.googleapis.com/token")
        scopes = data.get("scopes") or DEFAULT_GOOGLE_SCOPES

        if not refresh_token:
            return None

        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes
        )
        return creds
    except Exception as e:
        print(f"[EmailTool] Error loading credentials: {sanitize_text(str(e))}")
        return None


def get_gmail_service():
    """
    Builds the authenticated Google Gmail API service client.
    """
    from googleapiclient.discovery import build
    creds = load_gmail_credentials()
    if not creds:
        raise RuntimeError("Gmail OAuth credentials not configured. Please run setup_gmail_auth.py first.")
    return build("gmail", "v1", credentials=creds)


def send_email(to: str, subject: Optional[str] = None, body: Optional[str] = None) -> Dict[str, Any]:
    """
    Sends an email using the Gmail API (scope: gmail.send only).
    Validates recipient, enforces rate limits, encrypts secrets, and sanitizes API errors.
    """
    try:
        # 1. Validate inputs
        if not to or not isinstance(to, str):
            return {
                "status": "error",
                "action": "send_email",
                "message": "Recipient email address ('to') is required."
            }

        raw_parts = [p.strip() for p in re.split(r'[,;\s]+', to.strip()) if p.strip() and p.strip().lower() != "and"]
        to_clean = ", ".join(raw_parts)
        if not validate_email_format(to_clean):
            return {
                "status": "error",
                "action": "send_email",
                "message": f"Invalid recipient email format: '{to_clean}'. Must be a valid email (e.g. user@example.com)."
            }

        email_body = body if body is not None else ""
        email_subject = subject if subject and subject.strip() else auto_generate_subject(email_body)

        # 2. Rate limiting check
        can_send, rate_err = email_rate_limiter.can_send()
        if not can_send:
            return {
                "status": "error",
                "action": "send_email",
                "message": rate_err
            }

        # 3. Build RFC 2822 MIME message
        mime_msg = MIMEText(email_body, "plain", "utf-8")
        mime_msg["to"] = to_clean
        mime_msg["subject"] = email_subject
        mime_msg["from"] = "me"

        raw_encoded = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")

        # 4. Dispatch via Gmail API
        service = get_gmail_service()
        result = service.users().messages().send(
            userId="me",
            body={"raw": raw_encoded}
        ).execute()

        # Record successful dispatch for rate limiter
        email_rate_limiter.record_send()

        msg_id = result.get("id", "SENT")
        return {
            "status": "success",
            "action": "send_email",
            "message_id": msg_id,
            "to": to_clean,
            "subject": email_subject,
            "body": email_body,
            "message": f"Email successfully sent to {to_clean}."
        }

    except Exception as e:
        sanitized_err = sanitize_text(str(e))
        return {
            "status": "error",
            "action": "send_email",
            "message": f"Failed to send email: {sanitized_err}"
        }
