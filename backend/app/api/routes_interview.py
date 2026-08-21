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
from engine.db import save_interview_session, get_interview_session

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
    Persists Phase 1 interview configuration and initializes session.
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

@router.get("/{interview_id}")
async def get_interview(interview_id: str):
    """Retrieves an existing interview session."""
    session = get_interview_session(interview_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return {"status": "success", "data": session}
