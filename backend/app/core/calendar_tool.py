import os
import re
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import dateparser

from app.config import settings
from app.core.email_tool import load_gmail_credentials, GMAIL_TOKEN_PATH
from app.core.reminder_service import create_reminder, cancel_reminder_by_event_id
from app.core.sanitizer import sanitize_text

# Combined Google Scopes for Email & Calendar
CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly"
]

def get_calendar_service():
    """
    Builds the authenticated Google Calendar API v3 client.
    """
    from googleapiclient.discovery import build
    creds = load_gmail_credentials()
    if not creds:
        raise RuntimeError("Google Calendar OAuth credentials not configured. Please run setup_gmail_auth.py to authorize Calendar scopes.")
    return build("calendar", "v3", credentials=creds)


def parse_datetime_flexible(time_str: str) -> Optional[datetime]:
    """
    Parses natural language or ISO time strings into a datetime object.
    Defaults to future dates for relative references.
    """
    if not time_str or not isinstance(time_str, str):
        return None
    try:
        # First try ISO / standard format
        return datetime.fromisoformat(time_str)
    except Exception:
        pass

    # Natural language parsing
    dt = dateparser.parse(
        time_str,
        settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False}
    )
    return dt


def format_calendar_confirmation_reason(title: str, start_time: str, end_time: str, attendees: Optional[List[str]] = None) -> str:
    """
    Builds the standardized confirmation card text for calendar event creation.
    """
    attendees_str = ", ".join(attendees) if attendees else "(none specified)"
    return (
        f"CONFIRM ACTION: Create Calendar Event\n"
        f"Title: {title}\n"
        f"When: {start_time} – {end_time}\n"
        f"Attendees: {attendees_str}"
    )


def format_delete_confirmation_reason(event_id: str, title: Optional[str] = None) -> str:
    """
    Builds the confirmation card text for calendar event deletion.
    """
    title_str = f" ('{title}')" if title else ""
    return (
        f"CONFIRM ACTION: Delete Calendar Event\n"
        f"Event ID: {event_id}{title_str}\n"
        f"Warning: This will permanently delete the event from your Google Calendar."
    )


def check_calendar(date_range: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
    """
    Retrieves events from the user's primary Google Calendar.
    Read-only action; safe to execute automatically without confirmation.
    """
    try:
        service = get_calendar_service()

        now = datetime.now()
        time_min = now
        time_max = now + timedelta(days=2)

        if date_range:
            lower = date_range.lower().strip()
            if "today" in lower:
                time_min = datetime(now.year, now.month, now.day, 0, 0, 0)
                time_max = datetime(now.year, now.month, now.day, 23, 59, 59)
            elif "tomorrow" in lower:
                tom = now + timedelta(days=1)
                time_min = datetime(tom.year, tom.month, tom.day, 0, 0, 0)
                time_max = datetime(tom.year, tom.month, tom.day, 23, 59, 59)
            elif "week" in lower or "this week" in lower:
                time_min = now
                time_max = now + timedelta(days=7)
            else:
                parsed_dt = parse_datetime_flexible(date_range)
                if parsed_dt:
                    time_min = datetime(parsed_dt.year, parsed_dt.month, parsed_dt.day, 0, 0, 0)
                    time_max = datetime(parsed_dt.year, parsed_dt.month, parsed_dt.day, 23, 59, 59)

        # Convert to RFC3339 format with Z / local offset
        time_min_str = time_min.isoformat() + "Z" if not time_min.tzinfo else time_min.isoformat()
        time_max_str = time_max.isoformat() + "Z" if not time_max.tzinfo else time_max.isoformat()

        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min_str,
            timeMax=time_max_str,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        items = events_result.get("items", [])
        formatted_events = []
        for item in items:
            start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
            end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
            formatted_events.append({
                "id": item.get("id"),
                "summary": item.get("summary", "No Title"),
                "start": start,
                "end": end,
                "location": item.get("location"),
                "attendees": [a.get("email") for a in item.get("attendees", []) if "email" in a],
                "html_link": item.get("htmlLink")
            })

        count = len(formatted_events)
        msg = f"Found {count} event{'s' if count != 1 else ''} on your calendar."
        if count == 0:
            msg = "You have no scheduled events for this time period."

        return {
            "status": "success",
            "action": "check_calendar",
            "events_count": count,
            "events": formatted_events,
            "message": msg
        }

    except Exception as e:
        sanitized_err = sanitize_text(str(e))
        return {
            "status": "error",
            "action": "check_calendar",
            "message": f"Failed to check calendar: {sanitized_err}"
        }


def create_event(
    title: str,
    start_time: str,
    end_time: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    description: Optional[str] = None,
    duration_minutes: int = 30
) -> Dict[str, Any]:
    """
    Creates a new Google Calendar event.
    Mutating action; requires human confirmation before execution.
    """
    try:
        service = get_calendar_service()

        start_dt = parse_datetime_flexible(start_time)
        if not start_dt:
            return {
                "status": "error",
                "action": "create_event",
                "message": f"Unable to parse start time: '{start_time}'. Please provide a valid time/date."
            }

        if end_time:
            end_dt = parse_datetime_flexible(end_time)
            if not end_dt:
                end_dt = start_dt + timedelta(minutes=duration_minutes)
        else:
            end_dt = start_dt + timedelta(minutes=duration_minutes)

        event_body = {
            "summary": title.strip() if title else "Meeting",
            "description": description or "Created by Vocalis AI Assistant",
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "UTC"
            }
        }

        if attendees:
            event_body["attendees"] = [{"email": a.strip()} for a in attendees if a.strip()]

        created_event = service.events().insert(
            calendarId="primary",
            body=event_body
        ).execute()

        event_id = created_event.get("id")
        start_fmt = start_dt.strftime("%b %d, %Y at %I:%M %p")
        end_fmt = end_dt.strftime("%I:%M %p")

        # =========================================================================
        # Auto-Link Local Voice Alert Reminder (Default 10 mins before start)
        # =========================================================================
        offset_min = getattr(settings, "DEFAULT_MEETING_ALERT_MINUTES", 10)
        alert_dt = start_dt - timedelta(minutes=offset_min)
        now = datetime.now()

        linked_reminder_res = None
        if alert_dt > now:
            alert_text = f"Reminder: your meeting '{title}' starts in {offset_min} minutes."
            linked_reminder_res = create_reminder(
                text=alert_text,
                due_time=alert_dt.isoformat(),
                linked_event_id=event_id
            )
            print(f"[Activity] Calendar event created: \"{title}\" ({start_fmt}–{end_fmt})")
            print(f"[Activity] Linked voice alert scheduled for {alert_dt.strftime('%I:%M %p')}")
        elif start_dt > now:
            # Edge case: event starts in less than offset_min minutes from now
            minutes_left = max(1, int((start_dt - now).total_seconds() / 60))
            alert_text = f"Reminder: your meeting '{title}' starts shortly in {minutes_left} minutes."
            immediate_alert_dt = now + timedelta(seconds=5)
            linked_reminder_res = create_reminder(
                text=alert_text,
                due_time=immediate_alert_dt.isoformat(),
                linked_event_id=event_id
            )
            print(f"[Activity] Calendar event created: \"{title}\" ({start_fmt}–{end_fmt})")
            print(f"[Activity] Event starts in < {offset_min}m; scheduled immediate voice alert in 5s.")
        else:
            print(f"[Activity] Calendar event created: \"{title}\" (start time in past; skipped voice alert).")

        return {
            "status": "success",
            "action": "create_event",
            "event_id": event_id,
            "title": title,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "when_formatted": f"{start_fmt} – {end_fmt}",
            "linked_voice_alert": linked_reminder_res,
            "html_link": created_event.get("htmlLink"),
            "message": f"Calendar event '{title}' successfully created for {start_fmt} – {end_fmt} with automatic voice reminder."
        }

    except Exception as e:
        sanitized_err = sanitize_text(str(e))
        return {
            "status": "error",
            "action": "create_event",
            "message": f"Failed to create calendar event: {sanitized_err}"
        }


def delete_event(event_id: str) -> Dict[str, Any]:
    """
    Deletes a Google Calendar event by ID and cancels any auto-linked local voice alert reminder.
    Mutating action; requires human confirmation before execution.
    """
    try:
        if not event_id:
            return {
                "status": "error",
                "action": "delete_event",
                "message": "Event ID is required to delete a calendar event."
            }

        service = get_calendar_service()
        clean_event_id = event_id.strip()
        service.events().delete(calendarId="primary", eventId=clean_event_id).execute()

        # Cascade cancel any linked reminder
        cancel_reminder_by_event_id(clean_event_id)
        print(f"[Activity] Cancelled linked voice alert for calendar event ID: {clean_event_id}")

        return {
            "status": "success",
            "action": "delete_event",
            "event_id": clean_event_id,
            "message": f"Calendar event '{clean_event_id}' and its linked voice reminder have been deleted."
        }

    except Exception as e:
        sanitized_err = sanitize_text(str(e))
        return {
            "status": "error",
            "action": "delete_event",
            "message": f"Failed to delete calendar event: {sanitized_err}"
        }


def parse_calendar_command(text: str) -> Dict[str, Any]:
    """
    Parses natural calendar queries and requests.
    Identifies action ('check', 'create', 'delete'), along with extracted parameters.
    """
    q = text.strip()
    q_lower = q.lower()

    # 1. Check/List Intent
    if any(q_lower.startswith(p) for p in ["what's on my calendar", "whats on my calendar", "what is on my calendar", "check calendar", "check my calendar", "show my calendar", "am i free", "list events", "calendar for"]):
        date_range = "today"
        if "tomorrow" in q_lower:
            date_range = "tomorrow"
        elif "this week" in q_lower or "next week" in q_lower:
            date_range = "week"
        elif "today" in q_lower:
            date_range = "today"
        else:
            time_match = re.search(r'\b(?:at|on|for)\s+([a-zA-Z0-9\s:]+(?:am|pm|today|tomorrow)?)', q, re.I)
            if time_match:
                date_range = time_match.group(1).strip()

        return {
            "action": "check",
            "date_range": date_range
        }

    # 2. Delete / Cancel Intent
    if any(q_lower.startswith(p) for p in ["cancel my ", "cancel meeting", "cancel event", "delete meeting", "delete event", "delete calendar"]):
        event_id = None
        id_match = re.search(r'\b(?:id|event)\s*[:=]?\s*([a-zA-Z0-9_-]{10,})', q)
        if id_match:
            event_id = id_match.group(1).strip()
        
        target_info = re.sub(r'^(?:cancel|delete)\s+(?:my\s+)?(?:meeting|event|calendar\s+event)?\s*', '', q, flags=re.I).strip()
        return {
            "action": "delete",
            "event_id": event_id,
            "target": target_info
        }

    # 3. Create / Schedule Intent
    # e.g., "Schedule a meeting with John tomorrow at 3pm for 30 minutes"
    title = "Meeting"
    start_time = None
    end_time = None
    duration_min = 30
    attendees: List[str] = []

    # Extract attendees (emails)
    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', q)
    if emails:
        attendees = emails

    # Extract duration (e.g. for 30 minutes, for 1 hour)
    dur_match = re.search(r'\bfor\s+(\d+)\s*(min|minute|minutes|hour|hours|hr|hrs)\b', q_lower)
    if dur_match:
        qty = int(dur_match.group(1))
        unit = dur_match.group(2)
        if "hour" in unit or "hr" in unit:
            duration_min = qty * 60
        else:
            duration_min = qty

    # Extract title
    # Pattern: "Schedule (a/an) <title> (tomorrow|at|on|with)..."
    title_match = re.search(r'^(?:schedule|create|set\s+up|book)\s+(?:a\s+|an\s+)?(?:meeting\s+with\s+([a-zA-Z\s]+?)|event\s+([a-zA-Z\s]+?)|([a-zA-Z\s]+?))\s+(?:tomorrow|today|at|on|for|with)', q, re.I)
    if title_match:
        title = (title_match.group(1) or title_match.group(2) or title_match.group(3) or "Meeting").strip()
        if "meeting with" not in title.lower() and title_match.group(1):
            title = f"Meeting with {title}"
    else:
        # Fallback title extraction
        simple_title = re.sub(r'^(?:schedule|create|set\s+up|book)\s+(?:a\s+|an\s+)?', '', q, flags=re.I)
        parts = re.split(r'\s+(?:tomorrow|today|at|on|for)\s+', simple_title, flags=re.I)
        if parts and parts[0].strip():
            title = parts[0].strip().title()

    # Extract start time
    time_match = re.search(r'\b(tomorrow(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?|today(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?|\d{1,2}(?::\d{2})?\s*(?:am|pm)|next\s+[a-zA-Z]+(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?)\b', q_lower)
    if time_match:
        start_time = time_match.group(1).strip()
    else:
        start_time = "tomorrow at 3pm"

    return {
        "action": "create",
        "title": title or "Meeting",
        "start_time": start_time,
        "end_time": end_time,
        "duration_minutes": duration_min,
        "attendees": attendees
    }
