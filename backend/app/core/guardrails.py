import re
from typing import Tuple, Dict, Any, Optional

DESTRUCTIVE_ACTIONS = {
    "system_shutdown", "system_restart", "delete_file", "format_drive",
    "modify_registry", "kill_process", "send_unconfirmed_payment", "wipe_database",
    "fs_delete"
}

DANGEROUS_PATTERNS = [
    r"\brm\s+-(?:r|f|rf|fr)\b",
    r"\bdel\s+/[sfq]\b",
    r"\bformat\s+[a-z]:\b",
    r"\bshutdown\b",
    r"\bdrop\s+(?:table|database|schema)\b",
    r"\bkill\s+-9\b",
    r"\btaskkill\s+/f\b"
]

def evaluate_guardrails(
    intent: str,
    action_data: Optional[Dict[str, Any]] = None,
    confidence: float = 1.0,
    tool_name: Optional[str] = None,
    tool_args: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Evaluates whether an action is safe to execute automatically or requires
    human-in-the-loop explicit confirmation.
    """
    data = action_data or {}
    args = tool_args or {}
    action_type = tool_name or data.get("action", intent)
    
    # 1. Check email sending confirmation
    if action_type in ("send_email", "email_send"):
        to_addr = args.get("to") or data.get("to") or args.get("recipient_email") or data.get("recipient_email") or args.get("recipient_name") or data.get("recipient_name") or "unspecified"
        subject = args.get("subject") or data.get("subject") or "Message from Vocalis AI"
        body = args.get("body") or data.get("body") or ""
        reason = (
            f"CONFIRM ACTION: Send Email\n"
            f"To: {to_addr}\n"
            f"Subject: {subject}\n"
            f"Body: \"{body}\""
        )
        return False, reason

    # 2. Check calendar mutating actions (create / delete)
    if action_type in ("create_event", "calendar_create", "schedule_meeting"):
        title = args.get("title") or data.get("title") or "Meeting"
        start = args.get("start_time") or data.get("start_time") or "Tomorrow, 3:00 PM"
        end = args.get("end_time") or data.get("end_time") or "3:30 PM"
        when = args.get("when_formatted") or data.get("when_formatted") or f"{start} – {end}"
        attendees = args.get("attendees") or data.get("attendees") or []
        attendees_str = ", ".join(attendees) if attendees else "(none specified)"
        reason = (
            f"CONFIRM ACTION: Create Calendar Event\n"
            f"Title: {title}\n"
            f"When: {when}\n"
            f"Attendees: {attendees_str}"
        )
        return False, reason

    if action_type in ("delete_event", "calendar_delete", "cancel_meeting"):
        event_id = args.get("event_id") or data.get("event_id") or "unspecified"
        reason = (
            f"CONFIRM ACTION: Delete Calendar Event\n"
            f"Event ID: {event_id}\n"
            f"Warning: This will permanently delete the event from your Google Calendar."
        )
        return False, reason

    # 3. Check destructive action names
    if action_type in DESTRUCTIVE_ACTIONS:
        return False, f"Critical action '{action_type}' requires explicit human authorization."

    # 2. Check dangerous terminal command patterns
    if action_type == "terminal_exec":
        cmd = args.get("command", "") or data.get("command", "")
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return False, f"Command contains potentially destructive operation ('{cmd}'). Explicit human approval required."

    # 3. Check low confidence threshold
    if confidence < 0.70:
        return False, f"Confidence score ({round(confidence * 100)}%) is below the autonomous execution threshold (70%)."

    return True, None

