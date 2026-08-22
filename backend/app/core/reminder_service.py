import os
import re
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import dateparser
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

from engine.db import (
    add_reminder as db_add_reminder,
    get_reminders as db_get_reminders,
    get_reminder_by_id as db_get_reminder_by_id,
    get_reminder_by_event_id as db_get_reminder_by_event_id,
    update_reminder_status as db_update_reminder_status,
    cancel_reminder_by_event_id as db_cancel_reminder_by_event_id,
    delete_reminder as db_delete_reminder
)
from app.core.sanitizer import sanitize_text

logger = logging.getLogger("vocalis.reminders")

# Thread-safe global scheduler
_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.start()
        _load_pending_reminders_from_db()
    elif not _scheduler.running:
        _scheduler.start()
    return _scheduler


def _trigger_reminder_execution(reminder_id: int, reminder_text: str):
    """
    Callback invoked by APScheduler when a reminder is due.
    Updates DB status, logs to Activity Stream, and triggers vocal TTS notification.
    """
    try:
        logger.info(f"[REMINDER TRIGGERED] ID: {reminder_id} — '{reminder_text}'")
        db_update_reminder_status(reminder_id, "completed")

        # Vocalize reminder via SpeechService / TTS if available
        try:
            print(f"\n[🔔 VOCALIS VOICE ALERT]: {reminder_text}\n")
        except Exception as e:
            logger.warning(f"Failed to trigger reminder vocal alert: {e}")

    except Exception as e:
        logger.error(f"Error handling reminder trigger {reminder_id}: {sanitize_text(str(e))}")


def _load_pending_reminders_from_db():
    """
    Restores scheduled jobs from the SQLite database on startup.
    """
    try:
        pending = db_get_reminders(status_filter="pending")
        now = datetime.now()
        for r in pending:
            r_id = r["id"]
            r_text = r["text"]
            r_due = r["due_time"]
            try:
                due_dt = datetime.fromisoformat(r_due)
                if due_dt > now:
                    job_id = f"reminder_{r_id}"
                    if not _scheduler.get_job(job_id):
                        _scheduler.add_job(
                            _trigger_reminder_execution,
                            trigger=DateTrigger(run_date=due_dt),
                            args=[r_id, r_text],
                            id=job_id,
                            replace_existing=True
                        )
                else:
                    # Mark expired past reminders as completed or trigger them
                    db_update_reminder_status(r_id, "completed")
            except Exception as ex:
                logger.warning(f"Could not reschedule reminder {r_id}: {ex}")
    except Exception as e:
        logger.error(f"Failed to load pending reminders: {sanitize_text(str(e))}")


def parse_reminder_time(time_str: str) -> Optional[datetime]:
    """
    Parses natural language relative or absolute times (e.g. 'in 20 minutes', 'tomorrow at 9am', '5pm').
    """
    if not time_str or not isinstance(time_str, str):
        return None
    try:
        return datetime.fromisoformat(time_str)
    except Exception:
        pass

    # Use dateparser configured for future dates
    dt = dateparser.parse(
        time_str,
        settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False}
    )
    return dt


def create_reminder(text: str, due_time: str, linked_event_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Creates and schedules a local reminder, optionally linked to a calendar event.
    """
    try:
        clean_text = text.strip() if text else "Reminder"
        due_dt = parse_reminder_time(due_time)
        if not due_dt:
            return {
                "status": "error",
                "action": "create_reminder",
                "message": f"Could not understand the time expression: '{due_time}'. Please specify a time like 'in 20 minutes' or 'at 5pm'."
            }

        now = datetime.now()
        if due_dt <= now:
            # If past time was parsed, assume near future or next occurrence
            due_dt = due_dt.replace(day=due_dt.day + 1) if due_dt.day == now.day else due_dt

        iso_time = due_dt.isoformat()
        reminder_id = db_add_reminder(text=clean_text, due_time=iso_time, linked_event_id=linked_event_id)
        if not reminder_id:
            return {
                "status": "error",
                "action": "create_reminder",
                "message": "Failed to save reminder in the database."
            }

        # Schedule job
        scheduler = get_scheduler()
        job_id = f"reminder_{reminder_id}"
        scheduler.add_job(
            _trigger_reminder_execution,
            trigger=DateTrigger(run_date=due_dt),
            args=[reminder_id, clean_text],
            id=job_id,
            replace_existing=True
        )

        fmt_time = due_dt.strftime("%I:%M %p, %b %d") if due_dt.date() != now.date() else due_dt.strftime("%I:%M %p")
        return {
            "status": "success",
            "action": "create_reminder",
            "reminder_id": reminder_id,
            "text": clean_text,
            "due_time": iso_time,
            "due_time_formatted": fmt_time,
            "linked_event_id": linked_event_id,
            "message": f"Reminder set for {fmt_time}: '{clean_text}'."
        }

    except Exception as e:
        sanitized_err = sanitize_text(str(e))
        return {
            "status": "error",
            "action": "create_reminder",
            "message": f"Failed to create reminder: {sanitized_err}"
        }


def list_reminders(status_filter: Optional[str] = "pending") -> Dict[str, Any]:
    """
    Lists reminders from the local database.
    """
    try:
        reminders = db_get_reminders(status_filter=status_filter)
        count = len(reminders)
        msg = f"You have {count} {status_filter or ''} reminder{'s' if count != 1 else ''}."
        if count == 0:
            msg = f"No {status_filter or ''} reminders found."

        return {
            "status": "success",
            "action": "list_reminders",
            "count": count,
            "reminders": reminders,
            "message": msg
        }
    except Exception as e:
        sanitized_err = sanitize_text(str(e))
        return {
            "status": "error",
            "action": "list_reminders",
            "message": f"Failed to list reminders: {sanitized_err}"
        }


def cancel_reminder(reminder_id: int) -> Dict[str, Any]:
    """
    Cancels a reminder and unschedules its trigger job.
    """
    try:
        success = db_update_reminder_status(reminder_id, "cancelled")
        if not success:
            return {
                "status": "error",
                "action": "cancel_reminder",
                "message": f"Reminder #{reminder_id} not found."
            }

        # Unschedule job
        scheduler = get_scheduler()
        job_id = f"reminder_{reminder_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        return {
            "status": "success",
            "action": "cancel_reminder",
            "reminder_id": reminder_id,
            "message": f"Reminder #{reminder_id} has been cancelled."
        }
    except Exception as e:
        sanitized_err = sanitize_text(str(e))
        return {
            "status": "error",
            "action": "cancel_reminder",
            "message": f"Failed to cancel reminder: {sanitized_err}"
        }


def cancel_reminder_by_event_id(linked_event_id: str) -> Dict[str, Any]:
    """
    Cancels any reminder associated with a linked Google Calendar event.
    """
    try:
        existing = db_get_reminder_by_event_id(linked_event_id)
        if not existing:
            return {
                "status": "success",
                "action": "cancel_reminder_by_event_id",
                "message": f"No linked reminder found for event {linked_event_id}."
            }

        r_id = existing["id"]
        db_update_reminder_status(r_id, "cancelled")

        # Unschedule job from APScheduler
        scheduler = get_scheduler()
        job_id = f"reminder_{r_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        return {
            "status": "success",
            "action": "cancel_reminder_by_event_id",
            "reminder_id": r_id,
            "linked_event_id": linked_event_id,
            "message": f"Cancelled linked voice alert for event {linked_event_id}."
        }
    except Exception as e:
        sanitized_err = sanitize_text(str(e))
        return {
            "status": "error",
            "action": "cancel_reminder_by_event_id",
            "message": f"Failed to cancel linked reminder: {sanitized_err}"
        }
    except Exception as e:
        sanitized_err = sanitize_text(str(e))
        return {
            "status": "error",
            "action": "cancel_reminder",
            "message": f"Failed to cancel reminder: {sanitized_err}"
        }


def parse_reminder_command(text: str) -> Dict[str, Any]:
    """
    Extracts action ('create', 'list', 'cancel'), reminder text, and due time.
    
    Examples:
    - 'Remind me to submit the report at 5pm'
    - 'Remind me in 20 minutes to check the oven'
    - 'What are my reminders for today?'
    - 'Cancel my 5pm reminder' / 'Cancel reminder 3'
    """
    q = text.strip()
    q_lower = q.lower()

    # 1. List reminders
    if any(q_lower.startswith(p) for p in ["what are my reminders", "show my reminders", "list reminders", "get reminders", "any reminders"]):
        return {
            "action": "list",
            "status_filter": "pending"
        }

    # 2. Cancel reminder
    if q_lower.startswith("cancel ") and "reminder" in q_lower:
        id_match = re.search(r'\b(?:reminder|id|#)\s*(\d+)', q_lower)
        if id_match:
            return {
                "action": "cancel",
                "reminder_id": int(id_match.group(1))
            }
        # Look for time reference (e.g. cancel my 5pm reminder)
        time_match = re.search(r'\b(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b', q_lower)
        return {
            "action": "cancel",
            "time_query": time_match.group(1) if time_match else None
        }

    # 3. Create reminder
    # Pattern A: "Remind me in 20 minutes to check the oven"
    in_time_match = re.search(r'\bremind\s+me\s+in\s+([0-9]+\s+(?:min|minute|minutes|hour|hours|sec|seconds))\s+to\s+(.+)$', q, re.I)
    if in_time_match:
        due_time = f"in {in_time_match.group(1).strip()}"
        reminder_text = in_time_match.group(2).strip()
        return {
            "action": "create",
            "text": reminder_text,
            "due_time": due_time
        }

    # Pattern B: "Remind me to <text> at/in/on/tomorrow <time>"
    at_time_match = re.search(r'\bremind\s+(?:me\s+)?to\s+(.+?)\s+(at|in|on|by|tomorrow)\s+(.+)$', q, re.I)
    if at_time_match:
        reminder_text = at_time_match.group(1).strip()
        prep = at_time_match.group(2).strip()
        time_part = at_time_match.group(3).strip()
        due_time = f"{prep} {time_part}" if prep not in ["at", "on", "by"] else time_part
        return {
            "action": "create",
            "text": reminder_text,
            "due_time": due_time
        }

    # Pattern C: "Set a reminder for <text> at <time>"
    set_match = re.search(r'\b(?:set|create|add)\s+(?:a\s+)?reminder\s+(?:for|to)?\s*(.+?)\s+(?:at|in|on|by)\s+(.+)$', q, re.I)
    if set_match:
        return {
            "action": "create",
            "text": set_match.group(1).strip(),
            "due_time": set_match.group(2).strip()
        }

    # Fallback pattern
    clean_q = re.sub(r'^(?:remind\s+me\s+(?:to\s+)?|set\s+reminder\s+(?:for\s+)?)', '', q, flags=re.I).strip()
    return {
        "action": "create",
        "text": clean_q or "Reminder",
        "due_time": "in 1 hour"
    }
