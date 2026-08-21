import time
import uuid
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Header, Depends
from pydantic import BaseModel

from app.core.interview_extractor import (
    extract_text_from_file,
    parse_resume_with_ai,
    parse_job_description_with_ai,
    TECHNICAL_DOMAINS
)
from app.core.interview_engine import (
    generate_initial_question,
    evaluate_answer_and_next_turn,
    generate_final_evaluation_report
)
from engine.db import (
    save_interview_session,
    get_interview_session,
    update_interview_state,
    log_integrity_event,
    delete_interview_session,
    verify_session_token
)

logger = logging.getLogger("vocalis.interview")
router = APIRouter(prefix="/api/interview", tags=["Interview Protocol"])

def verify_interview_auth(
    interview_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    session_token: Optional[str] = Query(None)
) -> bool:
    """Validates session authorization token (Bearer header, x-session-token, or query param)."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif x_session_token:
        token = x_session_token.strip()
    elif session_token:
        token = session_token.strip()

    if not verify_session_token(interview_id, token):
        raise HTTPException(
            status_code=401,
            detail=f"Unauthorized: Access to interview '{interview_id}' requires a valid session authorization token."
        )
    return True


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

class IntegrityEventRequest(BaseModel):
    interview_id: str
    event_type: str
    duration_seconds: Optional[float] = 0.0
    details: Optional[str] = ""

class EndInterviewRequest(BaseModel):
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
    Persists interview configuration, generates session token, and initializes session.
    """
    interview_id = req.interview_id or f"VOCALIS-INT-{uuid.uuid4().hex[:8].upper()}"
    
    session_token = save_interview_session(
        interview_id=interview_id,
        resume_data=req.resume_data,
        job_description_data=req.job_description_data,
        domain=req.domain,
        experience_level=req.experience_level,
        programming_language=req.programming_language,
        status="ready"
    )
    
    if not session_token:
        raise HTTPException(status_code=500, detail="Failed to initialize interview session in database.")
        
    return {
        "status": "success",
        "interview_id": interview_id,
        "session_token": session_token,
        "message": "Interview protocol initialized and ready for assessment."
    }

@router.post("/start")
async def start_interview(req: StartInterviewRequest):
    """
    Begins the live interview session.
    """
    session = get_interview_session(req.interview_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
        
    if session.get("status") == "in_progress" and session.get("current_question"):
        return {"status": "success", "data": session}

    now = time.time()
    now_str = time.strftime("%H:%M:%S")
    
    first_q = generate_initial_question(session)
    
    initial_log = [
        {"timestamp": now_str, "event": "Candidate Profile Loaded", "details": f"{session.get('resume_data', {}).get('name', 'Candidate')} profile verified"},
        {"timestamp": now_str, "event": "Assessment Session Started", "details": f"Track: {session.get('domain')}, Strict Evaluation Active"},
        {"timestamp": now_str, "event": f"Question Generated [{first_q.get('category', 'CV')}]", "details": "Opening architectural inquiry"}
    ]
    
    update_interview_state(
        interview_id=req.interview_id,
        current_phase="introduction",
        current_question=first_q,
        questions_history=[],
        difficulty="medium",
        start_time=now,
        status="in_progress",
        activity_log=initial_log,
        integrity_events=[],
        integrity_score=10.0
    )
    
    updated_session = get_interview_session(req.interview_id)
    return {"status": "success", "data": updated_session}

@router.post("/answer")
async def submit_answer(req: SubmitAnswerRequest):
    """
    Submits candidate's answer for strict 0-10 evaluation and triggers adaptive next question.
    """
    session = get_interview_session(req.interview_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
        
    if session.get("status") != "in_progress":
        session["start_time"] = time.time()
        session["status"] = "in_progress"

    candidate_ans = req.answer.strip()
    if not candidate_ans:
        raise HTTPException(status_code=400, detail="Answer text cannot be empty.")

    current_q = session.get("current_question") or {
        "id": "Q-000",
        "text": "Initial Technical Inquiry",
        "category": "CV",
        "difficulty": "medium",
        "expected_concept": "Accurate technical walkthrough"
    }

    turn_result = evaluate_answer_and_next_turn(session, candidate_ans)
    
    # Record history with strict score and factual justification
    history = session.get("questions_history", [])
    history.append({
        "question_id": current_q.get("id"),
        "question_text": current_q.get("text"),
        "category": current_q.get("category", "TECHNICAL"),
        "difficulty": current_q.get("difficulty", "medium"),
        "expected_concept": current_q.get("expected_concept", turn_result.get("expected_concept")),
        "answer_text": candidate_ans,
        "score": turn_result.get("score", 5),
        "evaluation": turn_result.get("evaluation"),
        "decision": turn_result.get("decision"),
        "timestamp": time.strftime("%H:%M:%S")
    })
    
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
        "score": turn_result.get("score"),
        "evaluation": turn_result.get("evaluation"),
        "decision": turn_result.get("decision"),
        "data": updated_session
    }

@router.post("/next-question")
async def skip_or_next_question(req: NextQuestionRequest):
    """
    Advances to next question.
    """
    session = get_interview_session(req.interview_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
        
    turn_result = evaluate_answer_and_next_turn(session, "Candidate skipped this question.")
    
    history = session.get("questions_history", [])
    current_q = session.get("current_question", {})
    if current_q:
        history.append({
            "question_id": current_q.get("id"),
            "question_text": current_q.get("text"),
            "category": current_q.get("category", "TECHNICAL"),
            "difficulty": current_q.get("difficulty", "medium"),
            "expected_concept": current_q.get("expected_concept", "Technical competency"),
            "answer_text": "[Skipped by candidate]",
            "score": 0,
            "evaluation": "Question skipped with zero score.",
            "decision": "ASK_QUESTION",
            "timestamp": time.strftime("%H:%M:%S")
        })
        
    existing_log = session.get("activity_log", [])
    new_events = [
        {"timestamp": time.strftime("%H:%M:%S"), "event": "Question Skipped: 0/10", "details": "Candidate requested next question"},
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

@router.post("/integrity-event")
async def record_integrity_event(req: IntegrityEventRequest):
    """
    Records an integrity event (tab switch, fullscreen exit, blur) with duration and recalculates integrity score.
    """
    res = log_integrity_event(
        interview_id=req.interview_id,
        event_type=req.event_type,
        duration_seconds=req.duration_seconds or 0.0,
        details=req.details or ""
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res

@router.post("/end")
async def end_interview(req: EndInterviewRequest):
    """
    Finalizes the interview, executes strict comprehensive evaluation report, and returns full scorecard.
    """
    session = get_interview_session(req.interview_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
        
    # Generate final evaluation report
    report = generate_final_evaluation_report(session)
    
    # Persist status as complete and save final report
    update_interview_state(
        interview_id=req.interview_id,
        status="complete",
        current_phase="complete",
        final_evaluation=report
    )
    
    updated_session = get_interview_session(req.interview_id)
    return {
        "status": "success",
        "report": report,
        "session": updated_session
    }

@router.get("/{interview_id}/state")
async def get_interview_state(interview_id: str):
    """
    Retrieves the full server-side interview state.
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

@router.delete("/session/{interview_id}")
async def delete_candidate_interview(
    interview_id: str,
    confirm: bool = Query(False, description="Must be true to authorize deletion"),
    confirm_interview_id: str = Query("", description="Must match the target interview_id"),
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    session_token: Optional[str] = Query(None)
):
    """
    Permanently purges a candidate's complete interview records, resume data,
    answers, and evaluation scorecards from the database.
    Requires session token authorization and double confirmation to prevent unauthorized deletion.
    """
    # 1. Cryptographic session token authorization check
    verify_interview_auth(
        interview_id=interview_id,
        authorization=authorization,
        x_session_token=x_session_token,
        session_token=session_token
    )

    # 2. Accidental deletion confirmation check
    if not confirm or confirm_interview_id != interview_id:
        raise HTTPException(
            status_code=400,
            detail="Permanent deletion requires 'confirm=true' and matching 'confirm_interview_id' parameter."
        )

    # Audit log before deletion
    logger.warning(f"[PII DELETION] Purging all interview records for candidate interview_id='{interview_id}'")
    
    deleted = delete_interview_session(interview_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Interview session '{interview_id}' not found or already deleted.")
    
    return {
        "status": "success",
        "action": "delete_candidate_session",
        "interview_id": interview_id,
        "message": f"Interview record for '{interview_id}' has been permanently purged."
    }

