import os
import sqlite3
import json
import time
from typing import Optional, Dict, Any, List, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jarvis.db")

def init_db():
    con = sqlite3.connect(DB_PATH, timeout=15.0)
    cursor = con.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.execute("CREATE TABLE IF NOT EXISTS sys_command(id integer primary key, name VARCHAR(100), path VARCHAR(1000))")
    cursor.execute("CREATE TABLE IF NOT EXISTS web_command(id integer primary key, name VARCHAR(100), url VARCHAR(1000))")
    cursor.execute("CREATE TABLE IF NOT EXISTS contacts(id integer primary key, name VARCHAR(200), mobile_no VARCHAR(255), email VARCHAR(255) NULL)")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        due_time TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        linked_event_id TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    con.commit()

    # Schema migration helper for reminders table
    cursor.execute("PRAGMA table_info(reminders)")
    rem_cols = [row[1] for row in cursor.fetchall()]
    if "linked_event_id" not in rem_cols:
        cursor.execute("ALTER TABLE reminders ADD COLUMN linked_event_id TEXT DEFAULT NULL")
        con.commit()

    # Multi-User Foundation: Users and Revocable Sessions Tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        display_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at REAL NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    # Phase 2: Per-User Google OAuth Tokens & Persistent CSRF State Registry
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_oauth_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        refresh_token_enc TEXT NOT NULL,
        scopes TEXT NOT NULL,
        google_email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_oauth_user_id ON user_oauth_tokens(user_id)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS oauth_states (
        state TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    con.commit()
    
    # Interview Mode Sessions (Phase 1, 2, 3 & Integrity Evaluation)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interview_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        interview_id TEXT UNIQUE NOT NULL,
        user_id TEXT DEFAULT 'default_user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resume_data TEXT,
        job_description_data TEXT,
        domain TEXT,
        experience_level TEXT,
        programming_language TEXT,
        status TEXT DEFAULT 'initialized',
        current_phase TEXT DEFAULT 'introduction',
        current_question TEXT DEFAULT NULL,
        questions_history TEXT DEFAULT '[]',
        difficulty TEXT DEFAULT 'medium',
        start_time REAL DEFAULT NULL,
        duration_seconds INTEGER DEFAULT 3600,
        activity_log TEXT DEFAULT '[]',
        integrity_events TEXT DEFAULT '[]',
        integrity_score REAL DEFAULT 10.0,
        final_evaluation TEXT DEFAULT NULL
    )
    """)
    con.commit()
    
    # Schema migration helper for existing databases (adds new columns if missing)
    cursor.execute("PRAGMA table_info(interview_sessions)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    
    new_cols = {
        "current_phase": "TEXT DEFAULT 'introduction'",
        "current_question": "TEXT DEFAULT NULL",
        "questions_history": "TEXT DEFAULT '[]'",
        "difficulty": "TEXT DEFAULT 'medium'",
        "start_time": "REAL DEFAULT NULL",
        "duration_seconds": "INTEGER DEFAULT 3600",
        "activity_log": "TEXT DEFAULT '[]'",
        "integrity_events": "TEXT DEFAULT '[]'",
        "integrity_score": "REAL DEFAULT 10.0",
        "final_evaluation": "TEXT DEFAULT NULL",
        "session_token": "TEXT DEFAULT NULL"
    }
    
    for col_name, col_def in new_cols.items():
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE interview_sessions ADD COLUMN {col_name} {col_def}")
            except Exception as e:
                print(f"[DB] Migration note on column {col_name}: {e}")
                
    con.commit()
    con.close()

import uuid
from engine.vault import encrypt_data, decrypt_data

# Initialize tables on import
init_db()

def _decrypt_json(raw_val: Optional[str], default_val: Any = None) -> Any:
    """Helper to decrypt and deserialize encrypted JSON fields."""
    if not raw_val:
        return default_val
    try:
        decrypted = decrypt_data(raw_val)
        return json.loads(decrypted) if decrypted else default_val
    except Exception:
        try:
            return json.loads(raw_val)
        except Exception:
            return default_val

def save_interview_session(
    interview_id: str,
    resume_data: Dict[str, Any],
    job_description_data: Dict[str, Any],
    domain: str,
    experience_level: str,
    programming_language: str,
    status: str = "ready",
    session_token: Optional[str] = None
) -> Optional[str]:
    """
    Saves a new interview session with encrypted PII and returns the generated session authorization token.
    """
    token = session_token or f"tok_{uuid.uuid4().hex}"
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO interview_sessions 
        (interview_id, resume_data, job_description_data, domain, experience_level, programming_language, status, session_token)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interview_id,
            encrypt_data(json.dumps(resume_data)),
            encrypt_data(json.dumps(job_description_data)),
            domain,
            experience_level,
            programming_language,
            status,
            token
        ))
        con.commit()
        con.close()
        return token
    except Exception as e:
        print(f"[DB] Error saving interview session: {e}")
        return None

def verify_session_token(interview_id: str, token: Optional[str]) -> bool:
    """
    Verifies that the provided session authorization token matches the interview session.
    """
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        cursor.execute("SELECT session_token FROM interview_sessions WHERE interview_id = ?", (interview_id,))
        row = cursor.fetchone()
        con.close()
        if not row:
            return False
        stored_token = row[0]
        # Legacy session fallback: if no token stored, allow access
        if not stored_token:
            return True
        return stored_token == token
    except Exception as e:
        print(f"[DB] Error verifying session token: {e}")
        return False


def update_interview_state(
    interview_id: str,
    current_phase: Optional[str] = None,
    current_question: Optional[Dict[str, Any]] = None,
    questions_history: Optional[List[Dict[str, Any]]] = None,
    difficulty: Optional[str] = None,
    start_time: Optional[float] = None,
    status: Optional[str] = None,
    activity_log: Optional[List[Dict[str, Any]]] = None,
    integrity_events: Optional[List[Dict[str, Any]]] = None,
    integrity_score: Optional[float] = None,
    final_evaluation: Optional[Dict[str, Any]] = None
) -> bool:
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        
        updates = []
        params = []
        
        if current_phase is not None:
            updates.append("current_phase = ?")
            params.append(current_phase)
        if current_question is not None:
            updates.append("current_question = ?")
            params.append(encrypt_data(json.dumps(current_question)))
        if questions_history is not None:
            updates.append("questions_history = ?")
            params.append(encrypt_data(json.dumps(questions_history)))
        if difficulty is not None:
            updates.append("difficulty = ?")
            params.append(difficulty)
        if start_time is not None:
            updates.append("start_time = ?")
            params.append(start_time)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if activity_log is not None:
            updates.append("activity_log = ?")
            params.append(encrypt_data(json.dumps(activity_log)))
        if integrity_events is not None:
            updates.append("integrity_events = ?")
            params.append(encrypt_data(json.dumps(integrity_events)))
        if integrity_score is not None:
            updates.append("integrity_score = ?")
            params.append(integrity_score)
        if final_evaluation is not None:
            updates.append("final_evaluation = ?")
            params.append(encrypt_data(json.dumps(final_evaluation)))
            
        if not updates:
            con.close()
            return True
            
        params.append(interview_id)
        query = f"UPDATE interview_sessions SET {', '.join(updates)} WHERE interview_id = ?"
        cursor.execute(query, tuple(params))
        con.commit()
        con.close()
        return True
    except Exception as e:
        print(f"[DB] Error updating interview state: {e}")
        return False

def delete_interview_session(interview_id: str) -> bool:
    """
    Permanently deletes all candidate records and evaluation data for the given interview_id.
    """
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        cursor.execute("DELETE FROM interview_sessions WHERE interview_id = ?", (interview_id,))
        rows_affected = cursor.rowcount
        con.commit()
        con.close()
        return rows_affected > 0
    except Exception as e:
        print(f"[DB] Error deleting interview session '{interview_id}': {e}")
        return False

def log_integrity_event(
    interview_id: str,
    event_type: str,
    duration_seconds: float = 0,
    details: str = ""
) -> Dict[str, Any]:
    """
    Appends an integrity event to session and recalculates integrity score.
    """
    try:
        session = get_interview_session(interview_id)
        if not session:
            return {"status": "error", "message": "Session not found"}

        events = session.get("integrity_events", [])
        now_str = time.strftime("%H:%M:%S")
        
        event_entry = {
            "id": f"INT-EVT-{len(events) + 1}",
            "timestamp": now_str,
            "event_type": event_type,
            "duration_seconds": round(duration_seconds, 1),
            "details": details or f"{event_type} detected ({round(duration_seconds, 1)}s)"
        }
        events.append(event_entry)

        # Integrity scoring calculation (starts at 10.0, deducts based on severity/duration)
        tab_switches = sum(1 for e in events if "tab" in e["event_type"].lower() or "focus" in e["event_type"].lower())
        fullscreen_exits = sum(1 for e in events if "fullscreen" in e["event_type"].lower())
        total_time_away = sum(e.get("duration_seconds", 0) for e in events)

        # Gradual penalty formula (never drops below 1.0)
        penalty = (tab_switches * 0.75) + (fullscreen_exits * 1.0) + (total_time_away * 0.05)
        new_integrity_score = max(1.0, round(10.0 - penalty, 1))

        # Also log to activity stream
        activity_log = session.get("activity_log", [])
        activity_log.append({
            "timestamp": now_str,
            "event": f"Integrity Event: {event_type}",
            "details": f"Duration: {round(duration_seconds, 1)}s | Integrity: {new_integrity_score}/10"
        })

        update_interview_state(
            interview_id=interview_id,
            integrity_events=events,
            integrity_score=new_integrity_score,
            activity_log=activity_log
        )

        return {
            "status": "success",
            "event": event_entry,
            "integrity_score": new_integrity_score,
            "total_events": len(events)
        }
    except Exception as e:
        print(f"[DB] Error logging integrity event: {e}")
        return {"status": "error", "message": str(e)}

def get_interview_session(interview_id: str) -> Optional[Dict[str, Any]]:
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        cursor.execute("""
        SELECT 
            interview_id, created_at, resume_data, job_description_data, 
            domain, experience_level, programming_language, status,
            current_phase, current_question, questions_history, difficulty,
            start_time, duration_seconds, activity_log, integrity_events,
            integrity_score, final_evaluation, session_token
        FROM interview_sessions WHERE interview_id = ?
        """, (interview_id,))
        row = cursor.fetchone()
        con.close()
        if row:
            start_t = row[12]
            dur_sec = row[13] or 3600
            
            # Compute server-controlled time remaining
            time_remaining = dur_sec
            if start_t is not None:
                elapsed = time.time() - start_t
                time_remaining = max(0, int(dur_sec - elapsed))
                
            return {
                "interview_id": row[0],
                "created_at": row[1],
                "resume_data": _decrypt_json(row[2], default_val={}),
                "job_description_data": _decrypt_json(row[3], default_val={}),
                "domain": row[4],
                "experience_level": row[5],
                "programming_language": row[6],
                "status": row[7],
                "current_phase": row[8] or "introduction",
                "current_question": _decrypt_json(row[9], default_val=None),
                "questions_history": _decrypt_json(row[10], default_val=[]),
                "difficulty": row[11] or "medium",
                "start_time": start_t,
                "duration_seconds": dur_sec,
                "time_remaining": time_remaining,
                "activity_log": _decrypt_json(row[14], default_val=[]),
                "integrity_events": _decrypt_json(row[15], default_val=[]),
                "integrity_score": row[16] if row[16] is not None else 10.0,
                "final_evaluation": _decrypt_json(row[17], default_val=None),
                "session_token": row[18] if len(row) > 18 else None
            }
        return None
    except Exception as e:
        print(f"[DB] Error fetching interview session: {e}")
        return None

# ==================== REMINDERS & TASK MANAGEMENT ====================

def add_reminder(text: str, due_time: str, linked_event_id: Optional[str] = None) -> Optional[int]:
    """
    Inserts a new reminder into the database, optionally linked to a calendar event.
    """
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        cursor.execute(
            "INSERT INTO reminders (text, due_time, status, linked_event_id) VALUES (?, ?, 'pending', ?)",
            (text, due_time, linked_event_id)
        )
        reminder_id = cursor.lastrowid
        con.commit()
        con.close()
        return reminder_id
    except Exception as e:
        print(f"[DB] Error adding reminder: {e}")
        return None

def get_reminders(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves reminders, optionally filtered by status ('pending', 'completed', 'cancelled').
    """
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        if status_filter:
            cursor.execute(
                "SELECT id, text, due_time, status, linked_event_id, created_at FROM reminders WHERE LOWER(status) = ? ORDER BY due_time ASC",
                (status_filter.lower(),)
            )
        else:
            cursor.execute(
                "SELECT id, text, due_time, status, linked_event_id, created_at FROM reminders ORDER BY due_time ASC"
            )
        rows = cursor.fetchall()
        con.close()
        return [
            {
                "id": r[0],
                "text": r[1],
                "due_time": r[2],
                "status": r[3],
                "linked_event_id": r[4],
                "created_at": r[5]
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[DB] Error fetching reminders: {e}")
        return []

def get_reminder_by_id(reminder_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single reminder by its ID.
    """
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        cursor.execute(
            "SELECT id, text, due_time, status, linked_event_id, created_at FROM reminders WHERE id = ?",
            (reminder_id,)
        )
        row = cursor.fetchone()
        con.close()
        if row:
            return {
                "id": row[0],
                "text": row[1],
                "due_time": row[2],
                "status": row[3],
                "linked_event_id": row[4],
                "created_at": row[5]
            }
        return None
    except Exception as e:
        print(f"[DB] Error fetching reminder {reminder_id}: {e}")
        return None

def get_reminder_by_event_id(linked_event_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a reminder linked to a specific calendar event.
    """
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        cursor.execute(
            "SELECT id, text, due_time, status, linked_event_id, created_at FROM reminders WHERE linked_event_id = ?",
            (linked_event_id,)
        )
        row = cursor.fetchone()
        con.close()
        if row:
            return {
                "id": row[0],
                "text": row[1],
                "due_time": row[2],
                "status": row[3],
                "linked_event_id": row[4],
                "created_at": row[5]
            }
        return None
    except Exception as e:
        print(f"[DB] Error fetching reminder for event {linked_event_id}: {e}")
        return None

def update_reminder_status(reminder_id: int, status: str) -> bool:
    """
    Updates a reminder's status ('completed', 'cancelled', 'pending').
    """
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        cursor.execute(
            "UPDATE reminders SET status = ? WHERE id = ?",
            (status, reminder_id)
        )
        affected = cursor.rowcount
        con.commit()
        con.close()
        return affected > 0
    except Exception as e:
        print(f"[DB] Error updating reminder status: {e}")
        return False

def cancel_reminder_by_event_id(linked_event_id: str) -> bool:
    """
    Cancels any pending reminders linked to a specific calendar event.
    """
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        cursor.execute(
            "UPDATE reminders SET status = 'cancelled' WHERE linked_event_id = ? AND status = 'pending'",
            (linked_event_id,)
        )
        affected = cursor.rowcount
        con.commit()
        con.close()
        return affected > 0
    except Exception as e:
        print(f"[DB] Error cancelling reminder for event {linked_event_id}: {e}")
        return False

def delete_reminder(reminder_id: int) -> bool:
    """
    Deletes a reminder from the database.
    """
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        affected = cursor.rowcount
        con.commit()
        con.close()
        return affected > 0
    except Exception as e:
        print(f"[DB] Error deleting reminder: {e}")
        return False


# ==================== MULTI-USER & SESSION AUTH HELPERS ====================

def create_user(email: str, password_hash: str, display_name: Optional[str] = None) -> Optional[int]:
    """
    Creates a new user account. Returns user_id on success, None if duplicate email.
    """
    con = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        cursor = con.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
            (email.strip().lower(), password_hash, display_name.strip() if display_name else None)
        )
        user_id = cursor.lastrowid
        con.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    except Exception as e:
        print(f"[DB] Error creating user: {e}")
        return None
    finally:
        con.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a user by normalized email address.
    """
    con = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        cursor = con.cursor()
        cursor.execute(
            "SELECT id, email, password_hash, display_name, created_at FROM users WHERE email = ?",
            (email.strip().lower(),)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "email": row[1],
                "password_hash": row[2],
                "display_name": row[3] or row[1].split('@')[0],
                "created_at": row[4]
            }
        return None
    except Exception as e:
        print(f"[DB] Error fetching user by email: {e}")
        return None
    finally:
        con.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves a user by numeric user ID.
    """
    con = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        cursor = con.cursor()
        cursor.execute(
            "SELECT id, email, password_hash, display_name, created_at FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "email": row[1],
                "password_hash": row[2],
                "display_name": row[3] or row[1].split('@')[0],
                "created_at": row[4]
            }
        return None
    except Exception as e:
        print(f"[DB] Error fetching user by id: {e}")
        return None
    finally:
        con.close()


def create_session(user_id: int, token: str, expires_at: float) -> bool:
    """
    Stores a revocable server-side session token.
    """
    con = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        cursor = con.cursor()
        cursor.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at)
        )
        con.commit()
        return True
    except Exception as e:
        print(f"[DB] Error creating session: {e}")
        return False
    finally:
        con.close()


def get_session_user(token: str) -> Optional[Dict[str, Any]]:
    """
    Validates a session token and returns the associated user if active and not expired.
    """
    con = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        cursor = con.cursor()
        cursor.execute("""
            SELECT u.id, u.email, u.display_name, u.created_at, s.expires_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > ?
        """, (token, time.time()))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "email": row[1],
                "display_name": row[2] or row[1].split('@')[0],
                "created_at": row[3],
                "session_expires_at": row[4]
            }
        return None
    except Exception as e:
        print(f"[DB] Error validating session: {e}")
        return None
    finally:
        con.close()


def delete_session(token: str) -> bool:
    """
    Revokes a session token immediately (server-side invalidation).
    """
    con = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        cursor = con.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        affected = cursor.rowcount
        con.commit()
        return affected > 0
    except Exception as e:
        print(f"[DB] Error deleting session: {e}")
        return False
    finally:
        con.close()


def delete_expired_sessions() -> int:
    """
    Cleans up all expired session tokens.
    """
    con = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        cursor = con.cursor()
        cursor.execute("DELETE FROM sessions WHERE expires_at <= ?", (time.time(),))
        affected = cursor.rowcount
        con.commit()
        return affected
    except Exception as e:
        print(f"[DB] Error deleting expired sessions: {e}")
        return 0
    finally:
        con.close()


# ==================== PER-USER GOOGLE OAUTH HELPERS ====================

def save_user_oauth_token(
    user_id: int,
    refresh_token: str,
    scopes: List[str],
    google_email: Optional[str] = None
) -> bool:
    """
    Encrypts and saves or updates a user's Google OAuth refresh token.
    Uses Fernet encryption at rest.
    """
    con = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        cursor = con.cursor()
        refresh_token_enc = encrypt_data(refresh_token)
        scopes_json = json.dumps(scopes)

        cursor.execute("""
        INSERT INTO user_oauth_tokens (user_id, refresh_token_enc, scopes, google_email, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            refresh_token_enc = excluded.refresh_token_enc,
            scopes = excluded.scopes,
            google_email = COALESCE(excluded.google_email, user_oauth_tokens.google_email),
            updated_at = CURRENT_TIMESTAMP
        """, (user_id, refresh_token_enc, scopes_json, google_email))

        con.commit()
        return True
    except Exception as e:
        print(f"[DB] Error saving user OAuth token: {e}")
        return False
    finally:
        con.close()


def get_user_oauth_token(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves and decrypts a user's Google OAuth refresh token and scopes.
    """
    con = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        cursor = con.cursor()
        cursor.execute(
            "SELECT refresh_token_enc, scopes, google_email, updated_at FROM user_oauth_tokens WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        refresh_token = decrypt_data(row[0])
        try:
            scopes = json.loads(row[1]) if row[1] else []
        except Exception:
            scopes = []

        return {
            "user_id": user_id,
            "refresh_token": refresh_token,
            "scopes": scopes,
            "google_email": row[2],
            "updated_at": row[3]
        }
    except Exception as e:
        print(f"[DB] Error fetching user OAuth token: {e}")
        return None
    finally:
        con.close()


def delete_user_oauth_token(user_id: int) -> bool:
    """
    Deletes a user's Google OAuth tokens (disconnect).
    """
    con = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        cursor = con.cursor()
        cursor.execute("DELETE FROM user_oauth_tokens WHERE user_id = ?", (user_id,))
        affected = cursor.rowcount
        con.commit()
        return affected > 0
    except Exception as e:
        print(f"[DB] Error deleting user OAuth token: {e}")
        return False
    finally:
        con.close()


def is_user_oauth_connected(user_id: int) -> Tuple[bool, Optional[str]]:
    """
    Checks if a user has connected their Google account.
    Returns (True, google_email) or (False, None).
    """
    con = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        cursor = con.cursor()
        cursor.execute("SELECT google_email FROM user_oauth_tokens WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return True, row[0]
        return False, None
    except Exception as e:
        print(f"[DB] Error checking user OAuth status: {e}")
        return False, None
    finally:
        con.close()


# ==================== OAUTH CSRF STATE REGISTRY ====================

def save_oauth_state(state: str, user_id: int, expires_at: float) -> bool:
    """
    Persists a one-time CSRF OAuth state token bound to a specific user.
    """
    con = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        cursor = con.cursor()
        # Clean up any expired states first
        cursor.execute("DELETE FROM oauth_states WHERE expires_at <= ?", (time.time(),))
        cursor.execute(
            "INSERT INTO oauth_states (state, user_id, expires_at) VALUES (?, ?, ?)",
            (state, user_id, expires_at)
        )
        con.commit()
        return True
    except Exception as e:
        print(f"[DB] Error saving OAuth state: {e}")
        return False
    finally:
        con.close()


def consume_oauth_state(state: str) -> Optional[int]:
    """
    Validates and immediately deletes a one-time CSRF OAuth state token.
    Returns user_id if valid and unexpired, None otherwise.
    """
    con = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        cursor = con.cursor()
        cursor.execute(
            "SELECT user_id, expires_at FROM oauth_states WHERE state = ?",
            (state,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        user_id, expires_at = row
        # Delete immediately (one-time consumption)
        cursor.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        con.commit()

        if time.time() > expires_at:
            return None

        return user_id
    except Exception as e:
        print(f"[DB] Error consuming OAuth state: {e}")
        return None
    finally:
        con.close()