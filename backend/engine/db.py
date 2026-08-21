import os
import sqlite3
import json
import time
from typing import Optional, Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jarvis.db")

def init_db():
    con = sqlite3.connect(DB_PATH)
    cursor = con.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS sys_command(id integer primary key, name VARCHAR(100), path VARCHAR(1000))")
    cursor.execute("CREATE TABLE IF NOT EXISTS web_command(id integer primary key, name VARCHAR(100), url VARCHAR(1000))")
    cursor.execute("CREATE TABLE IF NOT EXISTS contacts(id integer primary key, name VARCHAR(200), mobile_no VARCHAR(255), email VARCHAR(255) NULL)")
    
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
        "final_evaluation": "TEXT DEFAULT NULL"
    }
    
    for col_name, col_def in new_cols.items():
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE interview_sessions ADD COLUMN {col_name} {col_def}")
            except Exception as e:
                print(f"[DB] Migration note on column {col_name}: {e}")
                
    con.commit()
    con.close()

# Initialize tables on import
init_db()

def save_interview_session(
    interview_id: str,
    resume_data: Dict[str, Any],
    job_description_data: Dict[str, Any],
    domain: str,
    experience_level: str,
    programming_language: str,
    status: str = "ready"
) -> bool:
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO interview_sessions 
        (interview_id, resume_data, job_description_data, domain, experience_level, programming_language, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            interview_id,
            json.dumps(resume_data),
            json.dumps(job_description_data),
            domain,
            experience_level,
            programming_language,
            status
        ))
        con.commit()
        con.close()
        return True
    except Exception as e:
        print(f"[DB] Error saving interview session: {e}")
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
            params.append(json.dumps(current_question))
        if questions_history is not None:
            updates.append("questions_history = ?")
            params.append(json.dumps(questions_history))
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
            params.append(json.dumps(activity_log))
        if integrity_events is not None:
            updates.append("integrity_events = ?")
            params.append(json.dumps(integrity_events))
        if integrity_score is not None:
            updates.append("integrity_score = ?")
            params.append(integrity_score)
        if final_evaluation is not None:
            updates.append("final_evaluation = ?")
            params.append(json.dumps(final_evaluation))
            
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
            integrity_score, final_evaluation
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
                "resume_data": json.loads(row[2]) if row[2] else {},
                "job_description_data": json.loads(row[3]) if row[3] else {},
                "domain": row[4],
                "experience_level": row[5],
                "programming_language": row[6],
                "status": row[7],
                "current_phase": row[8] or "introduction",
                "current_question": json.loads(row[9]) if row[9] else None,
                "questions_history": json.loads(row[10]) if row[10] else [],
                "difficulty": row[11] or "medium",
                "start_time": start_t,
                "duration_seconds": dur_sec,
                "time_remaining": time_remaining,
                "activity_log": json.loads(row[14]) if row[14] else [],
                "integrity_events": json.loads(row[15]) if row[15] else [],
                "integrity_score": row[16] if row[16] is not None else 10.0,
                "final_evaluation": json.loads(row[17]) if row[17] else None
            }
        return None
    except Exception as e:
        print(f"[DB] Error fetching interview session: {e}")
        return None