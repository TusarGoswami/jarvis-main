import os
import sqlite3
import json
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jarvis.db")

def init_db():
    con = sqlite3.connect(DB_PATH)
    cursor = con.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS sys_command(id integer primary key, name VARCHAR(100), path VARCHAR(1000))")
    cursor.execute("CREATE TABLE IF NOT EXISTS web_command(id integer primary key, name VARCHAR(100), url VARCHAR(1000))")
    cursor.execute("CREATE TABLE IF NOT EXISTS contacts(id integer primary key, name VARCHAR(200), mobile_no VARCHAR(255), email VARCHAR(255) NULL)")
    
    # Interview Mode Sessions (Phase 1)
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
        status TEXT DEFAULT 'initialized'
    )
    """)
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

def get_interview_session(interview_id: str) -> Optional[Dict[str, Any]]:
    try:
        con = sqlite3.connect(DB_PATH)
        cursor = con.cursor()
        cursor.execute("SELECT interview_id, created_at, resume_data, job_description_data, domain, experience_level, programming_language, status FROM interview_sessions WHERE interview_id = ?", (interview_id,))
        row = cursor.fetchone()
        con.close()
        if row:
            return {
                "interview_id": row[0],
                "created_at": row[1],
                "resume_data": json.loads(row[2]) if row[2] else {},
                "job_description_data": json.loads(row[3]) if row[3] else {},
                "domain": row[4],
                "experience_level": row[5],
                "programming_language": row[6],
                "status": row[7]
            }
        return None
    except Exception as e:
        print(f"[DB] Error fetching interview session: {e}")
        return None