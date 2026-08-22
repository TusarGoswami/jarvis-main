import os
import sys
import time
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.calendar_tool import (
    check_calendar,
    create_event,
    delete_event,
    parse_calendar_command,
    format_calendar_confirmation_reason,
    format_delete_confirmation_reason,
    parse_datetime_flexible
)
from app.core.reminder_service import (
    create_reminder,
    list_reminders,
    cancel_reminder,
    parse_reminder_command,
    parse_reminder_time,
    get_scheduler,
    _load_pending_reminders_from_db
)
from app.core.guardrails import evaluate_guardrails
from engine.db import init_db, add_reminder, get_reminders, update_reminder_status, delete_reminder, get_reminder_by_id, DB_PATH
import sqlite3


# ==============================================================================
# 1. GOOGLE CALENDAR TESTS (Mocked Google API)
# ==============================================================================

def test_calendar_command_parsing():
    # 1. Check intent
    res1 = parse_calendar_command("What's on my calendar today?")
    assert res1["action"] == "check"
    assert res1["date_range"] == "today"

    res2 = parse_calendar_command("Am I free tomorrow at 2pm?")
    assert res2["action"] == "check"
    assert "tomorrow" in res2["date_range"]

    # 2. Create intent
    res3 = parse_calendar_command("Schedule a meeting with John tomorrow at 3pm for 30 minutes")
    assert res3["action"] == "create"
    assert "John" in res3["title"]
    assert "3pm" in res3["start_time"]
    assert res3["duration_minutes"] == 30

    # 3. Delete intent
    res4 = parse_calendar_command("Cancel my 4pm meeting")
    assert res4["action"] == "delete"


def test_calendar_guardrails_blocks_unconfirmed_creation():
    safe, reason = evaluate_guardrails(
        intent="create_event",
        action_data={
            "title": "Meeting with John",
            "start_time": "Tomorrow, 3:00 PM",
            "end_time": "3:30 PM",
            "attendees": ["john@example.com"]
        },
        tool_name="create_event"
    )
    assert safe is False
    assert "CONFIRM ACTION: Create Calendar Event" in reason
    assert "Meeting with John" in reason
    assert "john@example.com" in reason


def test_calendar_guardrails_blocks_unconfirmed_deletion():
    safe, reason = evaluate_guardrails(
        intent="delete_event",
        action_data={"event_id": "evt_abc123"},
        tool_name="delete_event"
    )
    assert safe is False
    assert "CONFIRM ACTION: Delete Calendar Event" in reason
    assert "evt_abc123" in reason


def test_calendar_guardrails_allows_read_only():
    safe, reason = evaluate_guardrails(
        intent="check_calendar",
        action_data={"date_range": "today"},
        tool_name="check_calendar"
    )
    assert safe is True
    assert reason is None


@patch("app.core.calendar_tool.get_calendar_service")
def test_calendar_read_mocked(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    mock_service.events().list().execute.return_value = {
        "items": [
            {
                "id": "evt_1",
                "summary": "Project Sync",
                "start": {"dateTime": "2026-08-22T14:00:00Z"},
                "end": {"dateTime": "2026-08-22T14:30:00Z"},
                "location": "Google Meet",
                "attendees": [{"email": "colleague@company.com"}],
                "htmlLink": "https://calendar.google.com/event?eid=1"
            }
        ]
    }

    res = check_calendar(date_range="today")
    assert res["status"] == "success"
    assert res["events_count"] == 1
    assert res["events"][0]["summary"] == "Project Sync"
    assert "colleague@company.com" in res["events"][0]["attendees"]


@patch("app.core.calendar_tool.get_calendar_service")
def test_calendar_create_mocked(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    mock_service.events().insert().execute.return_value = {
        "id": "new_evt_999",
        "htmlLink": "https://calendar.google.com/event?eid=999"
    }

    res = create_event(
        title="Strategy Review",
        start_time="2026-08-23T15:00:00",
        duration_minutes=45,
        attendees=["lead@company.com"]
    )
    assert res["status"] == "success"
    assert res["event_id"] == "new_evt_999"
    assert res["title"] == "Strategy Review"


@patch("app.core.calendar_tool.get_calendar_service")
def test_calendar_delete_mocked(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    mock_service.events().delete().execute.return_value = {}

    res = delete_event(event_id="evt_to_delete_123")
    assert res["status"] == "success"
    assert res["event_id"] == "evt_to_delete_123"


# ==============================================================================
# 2. REMINDERS & TASK MANAGEMENT TESTS (Local SQLite + APScheduler)
# ==============================================================================

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute("DELETE FROM reminders")
        con.commit()
        con.close()
    except Exception:
        pass


def test_reminder_time_parsing_accuracy():
    # 1. Relative "in X minutes"
    dt_in_20 = parse_reminder_time("in 20 minutes")
    assert dt_in_20 is not None
    assert dt_in_20 > datetime.now()

    # 2. "tomorrow at 9am"
    dt_tom = parse_reminder_time("tomorrow at 9am")
    assert dt_tom is not None
    assert dt_tom > datetime.now()

    # 3. "5pm"
    dt_5pm = parse_reminder_time("5pm")
    assert dt_5pm is not None


def test_reminder_command_parsing():
    # 1. Pattern: "Remind me in 20 minutes to check the oven"
    res1 = parse_reminder_command("Remind me in 20 minutes to check the oven")
    assert res1["action"] == "create"
    assert res1["text"] == "check the oven"
    assert "20 min" in res1["due_time"]

    # 2. Pattern: "Remind me to submit the report at 5pm"
    res2 = parse_reminder_command("Remind me to submit the report at 5pm")
    assert res2["action"] == "create"
    assert res2["text"] == "submit the report"
    assert "5pm" in res2["due_time"]

    # 3. Pattern: "What are my reminders for today?"
    res3 = parse_reminder_command("What are my reminders for today?")
    assert res3["action"] == "list"

    # 4. Pattern: "Cancel reminder 5"
    res4 = parse_reminder_command("Cancel reminder 5")
    assert res4["action"] == "cancel"
    assert res4["reminder_id"] == 5


def test_reminder_creation_and_listing():
    res = create_reminder(text="Buy groceries", due_time="in 30 minutes")
    assert res["status"] == "success"
    assert res["reminder_id"] is not None
    assert res["text"] == "Buy groceries"

    # List reminders
    list_res = list_reminders(status_filter="pending")
    assert list_res["status"] == "success"
    assert any(r["id"] == res["reminder_id"] for r in list_res["reminders"])


def test_reminder_cancellation():
    res = create_reminder(text="Call Dentist", due_time="in 45 minutes")
    r_id = res["reminder_id"]

    cancel_res = cancel_reminder(reminder_id=r_id)
    assert cancel_res["status"] == "success"
    assert cancel_res["reminder_id"] == r_id

    # Verify status in DB
    updated = get_reminder_by_id(r_id)
    assert updated["status"] == "cancelled"


def test_reminder_scheduler_trigger_execution():
    """
    Sets a reminder due in 1 second and asserts it executes and marks status completed.
    """
    due_time = (datetime.now() + timedelta(seconds=1)).isoformat()
    r_id = add_reminder("Urgent Test Ping", due_time)
    assert r_id is not None

    scheduler = get_scheduler()
    from app.core.reminder_service import _trigger_reminder_execution
    from apscheduler.triggers.date import DateTrigger

    scheduler.add_job(
        _trigger_reminder_execution,
        trigger=DateTrigger(run_date=datetime.fromisoformat(due_time)),
        args=[r_id, "Urgent Test Ping"],
        id=f"test_trigger_{r_id}"
    )

    # Wait 2 seconds for scheduler execution
    time.sleep(2.0)

    # Verify DB status updated to 'completed'
    record = get_reminder_by_id(r_id)
    assert record is not None
    assert record["status"] == "completed"


def test_reminder_persistence_across_restart():
    """
    Simulates reloading pending reminders on backend startup.
    """
    future_time = (datetime.now() + timedelta(hours=2)).isoformat()
    r_id = add_reminder("Persistent Task Across Reboot", future_time)

    # Simulate restart by loading DB reminders into scheduler
    _load_pending_reminders_from_db()

    scheduler = get_scheduler()
    job = scheduler.get_job(f"reminder_{r_id}")
    assert job is not None
    assert job.name is not None


# ==============================================================================
# 3. AUTO-LINKED CALENDAR VOICE ALERTS & CASCADE TESTS
# ==============================================================================

@patch("app.core.calendar_tool.get_calendar_service")
def test_calendar_event_auto_creates_linked_reminder(mock_get_service):
    """
    Asserts creating a calendar event automatically creates a linked reminder
    scheduled for exactly (event_start - DEFAULT_MEETING_ALERT_MINUTES).
    """
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    mock_service.events().insert().execute.return_value = {
        "id": "evt_auto_link_101",
        "htmlLink": "https://calendar.google.com/event?eid=101"
    }

    start_time = (datetime.now() + timedelta(hours=3)).replace(microsecond=0)
    res = create_event(
        title="Sprint Retrospective",
        start_time=start_time.isoformat(),
        duration_minutes=30
    )

    assert res["status"] == "success"
    assert res["event_id"] == "evt_auto_link_101"
    assert res["linked_voice_alert"] is not None

    # Verify linked reminder exists in database
    linked_rem = get_reminders(status_filter="pending")
    matching = [r for r in linked_rem if r.get("linked_event_id") == "evt_auto_link_101"]
    assert len(matching) == 1
    assert "Sprint Retrospective" in matching[0]["text"]
    assert "starts in 10 minutes" in matching[0]["text"]


@patch("app.core.calendar_tool.get_calendar_service")
def test_calendar_event_deletion_cascade_cancels_reminder(mock_get_service):
    """
    Asserts deleting a calendar event automatically cancels its linked reminder.
    """
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    mock_service.events().insert().execute.return_value = {
        "id": "evt_to_cascade_202",
        "htmlLink": "https://calendar.google.com/event?eid=202"
    }
    mock_service.events().delete().execute.return_value = {}

    start_time = (datetime.now() + timedelta(hours=4)).replace(microsecond=0)
    create_res = create_event(
        title="Executive Briefing",
        start_time=start_time.isoformat()
    )
    event_id = create_res["event_id"]

    # Verify linked reminder is pending
    rem_before = [r for r in get_reminders(status_filter="pending") if r.get("linked_event_id") == event_id]
    assert len(rem_before) == 1

    # Delete the calendar event
    del_res = delete_event(event_id=event_id)
    assert del_res["status"] == "success"

    # Verify linked reminder is now cancelled
    rem_after = [r for r in get_reminders(status_filter="pending") if r.get("linked_event_id") == event_id]
    assert len(rem_after) == 0


@patch("app.core.calendar_tool.get_calendar_service")
def test_calendar_event_starting_soon_fallback_behavior(mock_get_service):
    """
    Asserts creating an event starting in < 10 minutes schedules an immediate
    voice alert in 5 seconds with clear logging and does not fail.
    """
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    mock_service.events().insert().execute.return_value = {
        "id": "evt_soon_303",
        "htmlLink": "https://calendar.google.com/event?eid=303"
    }

    # Event starts in 5 minutes
    start_time = (datetime.now() + timedelta(minutes=5)).replace(microsecond=0)
    res = create_event(
        title="Quick Standup",
        start_time=start_time.isoformat()
    )

    assert res["status"] == "success"
    assert res["linked_voice_alert"] is not None
    assert "Quick Standup" in res["linked_voice_alert"]["text"]
    assert "starts shortly" in res["linked_voice_alert"]["text"]
