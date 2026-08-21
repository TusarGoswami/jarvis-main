import time
import uuid
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from app.core.interview_extractor import (
    extract_text_from_file,
    parse_resume_with_ai,
    parse_job_description_with_ai,
    TECHNICAL_DOMAINS
)
from app.core.interview_engine import (
    generate_initial_question,
    evaluate_answer_and_next_turn
)
from engine.db import (
    save_interview_session,
    get_interview_session,
    update_interview_state
)

router = APIRouter(prefix="/api/interview", tags=["Interview Protocol"])

class TextUploadRequest(BaseModel):
    text: str

class CreateInterviewRequest(BaseModel):
    interview_id: Optional[str] = None
    resume_data: Dict[str, Any]
    job_description_data: Dict[str, Any]
    domain: str
    experience_level: str
    programming_language: str

class StartInterviewRequest(BaseModel):
    interview_id: str

class SubmitAnswerRequest(BaseModel):
    interview_id: str
    answer: str

class NextQuestionRequest(BaseModel):
    interview_id: str

@router.get("/domains")
async def get_domains():
    """Returns the list of supported technical domains."""
    return {"domains": TECHNICAL_DOMAINS}

@router.post("/upload-resume")
async def upload_resume(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None)
):
    """
    Intake endpoint for Candidate CV / Resume.
    Accepts PDF, DOCX, TXT files or pasted text.
    Returns structured candidate profile.
    """
    try:
        content_text = ""
        filename = "resume.txt"
        
        if file:
            filename = file.filename or "resume.pdf"
            file_bytes = await file.read()
            if not file_bytes:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            content_text = extract_text_from_file(file_bytes, filename)
        elif raw_text:
            content_text = raw_text.strip()
        else:
            raise HTTPException(status_code=400, detail="Please upload a file (.pdf, .docx, .txt) or provide resume text.")

        if len(content_text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Extracted document text is too short or could not be read.")

        # Structured Extraction
        profile = parse_resume_with_ai(content_text)
        return {
            "status": "success",
            "filename": filename,
            "char_count": len(content_text),
            "data": profile
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process resume: {str(e)}")

@router.post("/upload-jd")
async def upload_job_description(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None)
):
    """
    Intake endpoint for Job Description.
    Accepts PDF, DOCX, TXT files or pasted text.
    Returns structured job requirements and auto-detected domain.
    """
    try:
        content_text = ""
        filename = "job_description.txt"

        if file:
            filename = file.filename or "job_description.pdf"
            file_bytes = await file.read()
            if not file_bytes:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            content_text = extract_text_from_file(file_bytes, filename)
        elif raw_text:
            content_text = raw_text.strip()
        else:
            raise HTTPException(status_code=400, detail="Please upload a file (.pdf, .docx, .txt) or provide job description text.")

        if len(content_text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Extracted document text is too short or could not be read.")

        # Structured Extraction & Domain Detection
        jd_spec = parse_job_description_with_ai(content_text)
        return {
            "status": "success",
            "filename": filename,
            "char_count": len(content_text),
            "data": jd_spec
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process job description: {str(e)}")

@router.post("/create")
async def create_interview(req: CreateInterviewRequest):
    """
    Persists interview configuration and initializes session.
    """
    interview_id = req.interview_id or f"VOCALIS-INT-{uuid.uuid4().hex[:8].upper()}"
    
    success = save_interview_session(
        interview_id=interview_id,
        resume_data=req.resume_data,
        job_description_data=req.job_description_data,
        domain=req.domain,
        experience_level=req.experience_level,
        programming_language=req.programming_language,
        status="ready"
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to initialize interview session in database.")
        
    return {
        "status": "success",
        "interview_id": interview_id,
        "message": "Interview protocol initialized and ready for Phase 2 assessment."
    }

# ─── PHASE 2 ADAPTIVE INTERVIEW ENGINE ENDPOINTS ───

@router.post("/start")
async def start_interview(req: StartInterviewRequest):
    """
    Begins the live interview session.
    Sets start_time (server-authoritative), status='in_progress', generates opening question.
    """
    session = get_interview_session(req.interview_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
        
    # If session already in progress, return current state directly (resumption)
    if session.get("status") == "in_progress" and session.get("current_question"):
        return {"status": "success", "data": session}

    now = time.time()
    now_str = time.strftime("%H:%M:%S")
    
    # Generate initial question
    first_q = generate_initial_question(session)
    
    initial_log = [
        {"timestamp": now_str, "event": "Candidate Profile Loaded", "details": f"{session.get('resume_data', {}).get('name', 'Candidate')} profile verified"},
        {"timestamp": now_str, "event": "Assessment Session Started", "details": f"Track: {session.get('domain')}, Difficulty: MEDIUM"},
        {"timestamp": now_str, "event": "Question Generated [CV]", "details": "Opening introduction and project architecture"}
    ]
    
    update_interview_state(
        interview_id=req.interview_id,
        current_phase="introduction",
        current_question=first_q,
        questions_history=[],
        difficulty="medium",
        start_time=now,
        status="in_progress",
        activity_log=initial_log
    )
    
    updated_session = get_interview_session(req.interview_id)
    return {"status": "success", "data": updated_session}

@router.post("/answer")
async def submit_answer(req: SubmitAnswerRequest):
    """
    Submits candidate's answer for evaluation and triggers adaptive next question generation.
    """
    session = get_interview_session(req.interview_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
        
    if session.get("status") != "in_progress":
        # Auto-start if not started yet
        session["start_time"] = time.time()
        session["status"] = "in_progress"

    candidate_ans = req.answer.strip()
    if not candidate_ans:
        raise HTTPException(status_code=400, detail="Answer text cannot be empty.")

    current_q = session.get("current_question") or {
        "id": "Q-000",
        "text": "Initial Introduction",
        "category": "CV",
        "difficulty": "medium"
    }

    # Evaluate answer and generate next turn
    turn_result = evaluate_answer_and_next_turn(session, candidate_ans)
    
    # Record history
    history = session.get("questions_history", [])
    history.append({
        "question_id": current_q.get("id"),
        "question_text": current_q.get("text"),
        "category": current_q.get("category", "TECHNICAL"),
        "difficulty": current_q.get("difficulty", "medium"),
        "answer_text": candidate_ans,
        "evaluation": turn_result.get("evaluation"),
        "decision": turn_result.get("decision"),
        "timestamp": time.strftime("%H:%M:%S")
    })
    
    # Append events to activity log
    existing_log = session.get("activity_log", [])
    new_events = turn_result.get("events", [])
    updated_log = existing_log + new_events
    
    new_phase = turn_result.get("new_phase", session.get("current_phase", "introduction"))
    new_diff = turn_result.get("new_difficulty", session.get("difficulty", "medium"))
    next_q = turn_result.get("next_question")
    
    is_complete = new_phase == "complete"
    session_status = "complete" if is_complete else "in_progress"
    
    update_interview_state(
        interview_id=req.interview_id,
        current_phase=new_phase,
        current_question=next_q,
        questions_history=history,
        difficulty=new_diff,
        status=session_status,
        activity_log=updated_log
    )
    
    updated_session = get_interview_session(req.interview_id)
    return {
        "status": "success",
        "evaluation": turn_result.get("evaluation"),
        "decision": turn_result.get("decision"),
        "data": updated_session
    }

@router.post("/next-question")
async def skip_or_next_question(req: NextQuestionRequest):
    """
    Advances to next adaptive question without a full answer (or for manual progression).
    """
    session = get_interview_session(req.interview_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
        
    turn_result = evaluate_answer_and_next_turn(session, "Skipped to next question.")
    
    history = session.get("questions_history", [])
    current_q = session.get("current_question", {})
    if current_q:
        history.append({
            "question_id": current_q.get("id"),
            "question_text": current_q.get("text"),
            "category": current_q.get("category", "TECHNICAL"),
            "difficulty": current_q.get("difficulty", "medium"),
            "answer_text": "[Skipped by candidate]",
            "evaluation": "Candidate requested next question.",
            "decision": "ASK_QUESTION",
            "timestamp": time.strftime("%H:%M:%S")
        })
        
    existing_log = session.get("activity_log", [])
    new_events = [
        {"timestamp": time.strftime("%H:%M:%S"), "event": "Question Skipped", "details": "Candidate requested next question"},
        {"timestamp": time.strftime("%H:%M:%S"), "event": f"Question Generated [{turn_result.get('next_question', {}).get('category', 'TECHNICAL')}]", "details": f"Difficulty: {turn_result.get('new_difficulty', 'medium').upper()}"}
    ]
    
    update_interview_state(
        interview_id=req.interview_id,
        current_phase=turn_result.get("new_phase", "cv_questions"),
        current_question=turn_result.get("next_question"),
        questions_history=history,
        difficulty=turn_result.get("new_difficulty", "medium"),
        activity_log=existing_log + new_events
    )
    
    updated_session = get_interview_session(req.interview_id)
    return {"status": "success", "data": updated_session}

@router.get("/{interview_id}/state")
async def get_interview_state(interview_id: str):
    """
    Retrieves the full server-side interview state including calculated remaining time.
    """
    session = get_interview_session(interview_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return {"status": "success", "data": session}

@router.get("/{interview_id}")
async def get_interview(interview_id: str):
    """Retrieves an existing interview session."""
    session = get_interview_session(interview_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return {"status": "success", "data": session}
