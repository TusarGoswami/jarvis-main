import json
import time
import uuid
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from app.config import settings

# Supported Question Categories
CATEGORIES = ["CV", "TECHNICAL", "DOMAIN", "BEHAVIORAL", "FOLLOW_UP"]

# Phase Durations / Thresholds (in elapsed minutes)
PHASE_TIMINGS = {
    "introduction": (0, 5),
    "cv_questions": (5, 25),
    "domain_questions": (25, 48),
    "behavioral": (48, 57),
    "complete": (57, 60),
}

def _get_ai_client():
    if settings.GEMINI_API_KEY:
        return genai.Client(api_key=settings.GEMINI_API_KEY)
    return None

def _get_timestamp_str():
    return time.strftime("%H:%M:%S")

def determine_phase_by_elapsed(elapsed_seconds: float, current_phase: str, questions_count: int) -> str:
    """
    Computes interview phase based on elapsed time and question milestones.
    """
    elapsed_minutes = elapsed_seconds / 60.0
    
    if elapsed_minutes >= 57 or questions_count >= 15:
        return "complete"
    elif elapsed_minutes >= 48 or (current_phase == "domain_questions" and questions_count >= 10):
        return "behavioral"
    elif elapsed_minutes >= 25 or (current_phase == "cv_questions" and questions_count >= 5):
        return "domain_questions"
    elif elapsed_minutes >= 5 or (current_phase == "introduction" and questions_count >= 1):
        return "cv_questions"
    
    return current_phase or "introduction"

def generate_initial_question(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates the opening introductory/CV question for the session.
    """
    resume = session.get("resume_data", {})
    jd = session.get("job_description_data", {})
    domain = session.get("domain", "Software Engineering")
    candidate_name = resume.get("name", "Candidate")
    projects = resume.get("projects", [])
    skills = resume.get("skills", [])
    
    client = _get_ai_client()
    if client:
        prompt = f"""
        You are an elite, empathetic, and rigorous Technical AI Interviewer conducting a real technical interview.
        Candidate Name: {candidate_name}
        Target Domain: {domain}
        Candidate Projects: {json.dumps(projects)}
        Candidate Skills: {json.dumps(skills[:8])}
        Job Role: {jd.get('title', 'Software Engineer')}

        Generate a warm yet professional opening question that Welcomes the candidate and asks them to introduce themselves and discuss the most impactful technical project listed on their CV.

        Respond ONLY with a valid JSON object matching this schema:
        {{
            "text": "The spoken/written opening interview question",
            "category": "CV",
            "difficulty": "medium",
            "context": "Opening introduction and CV project walkthrough"
        }}
        """
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    response_mime_type="application/json",
                )
            )
            parsed = json.loads(response.text)
            return {
                "id": f"Q-{uuid.uuid4().hex[:6].upper()}",
                "text": parsed.get("text", f"Welcome {candidate_name}. To begin our technical assessment, could you introduce yourself and walk me through the architecture of your primary project?"),
                "category": parsed.get("category", "CV"),
                "difficulty": parsed.get("difficulty", "medium"),
                "context": parsed.get("context", "Opening introduction"),
                "timestamp": _get_timestamp_str()
            }
        except Exception as e:
            print(f"[InterviewEngine] AI Initial Question error: {e}, using fallback generator.")

    # Fallback Opening Question
    project_title = projects[0].get("title", "your featured project") if projects else "your key project"
    return {
        "id": f"Q-{uuid.uuid4().hex[:6].upper()}",
        "text": f"Welcome {candidate_name} to your Vocalis AI technical interview for the {domain} track. To start, could you introduce yourself and explain the technical architecture and your specific contributions to {project_title}?",
        "category": "CV",
        "difficulty": "medium",
        "context": "Opening introduction and CV project walkthrough",
        "timestamp": _get_timestamp_str()
    }

def evaluate_answer_and_next_turn(session: Dict[str, Any], candidate_answer: str) -> Dict[str, Any]:
    """
    Evaluates candidate's answer, adjusts difficulty, and generates the next adaptive question.
    """
    resume = session.get("resume_data", {})
    jd = session.get("job_description_data", {})
    domain = session.get("domain", "Software Engineering")
    current_q = session.get("current_question", {})
    history = session.get("questions_history", [])
    current_diff = session.get("difficulty", "medium")
    current_phase = session.get("current_phase", "introduction")
    start_time = session.get("start_time") or time.time()
    
    elapsed_seconds = time.time() - start_time
    total_answered = len(history) + 1
    new_phase = determine_phase_by_elapsed(elapsed_seconds, current_phase, total_answered)
    
    client = _get_ai_client()
    if client and len(candidate_answer.strip()) > 3:
        prompt = f"""
        You are an elite, adaptive Technical AI Interviewer conducting a live interview.
        
        Session Parameters:
        - Target Domain: {domain}
        - Current Phase: {new_phase}
        - Current Difficulty: {current_diff}
        - Candidate Skills: {json.dumps(resume.get('skills', [])[:10])}
        - Candidate Projects: {json.dumps(resume.get('projects', []))}
        - Job Required Skills: {json.dumps(jd.get('required_skills', [])[:8])}
        
        Last Question Asked:
        \"{current_q.get('text', '')}\"
        
        Candidate's Answer:
        \"{candidate_answer}\"
        
        Previous Questions Asked in this interview:
        {json.dumps([h.get('question_text', '') for h in history])}
        
        Your Goal:
        1. Evaluate the candidate's answer for technical depth, specificity, and correctness.
        2. Decide the next action:
           - "FOLLOW_UP": If the candidate mentioned a specific technology, architecture, or tradeoff that warrants immediate probing.
           - "INCREASE_DIFFICULTY": If the answer was exceptionally thorough and confident.
           - "DECREASE_DIFFICULTY": If the answer was superficial, incorrect, or uncertain.
           - "ASK_QUESTION": Move to another core skill/requirement.
           - "MOVE_TO_NEXT_SECTION": If section questions are sufficient.
           - "END_INTERVIEW": If {new_phase == 'complete'}.
        3. Formulate the next question. It MUST be:
           - Highly specific to their CV projects or the JD technical requirements.
           - If category is FOLLOW_UP, directly reference details in their last answer.
           - NEVER repeat any question from the previous questions list.
           - Formatted professionally and concisely.

        Respond ONLY with a valid JSON object matching this schema:
        {{
            "evaluation_summary": "1-sentence assessment of the candidate's response",
            "decision": "FOLLOW_UP | INCREASE_DIFFICULTY | DECREASE_DIFFICULTY | ASK_QUESTION | MOVE_TO_NEXT_SECTION | END_INTERVIEW",
            "new_difficulty": "easy | medium | hard",
            "next_question_text": "The next question to ask",
            "next_question_category": "CV | TECHNICAL | DOMAIN | BEHAVIORAL | FOLLOW_UP",
            "next_question_context": "Reasoning for choosing this question"
        }}
        """
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.25,
                    response_mime_type="application/json",
                )
            )
            parsed = json.loads(response.text)
            
            decision = parsed.get("decision", "ASK_QUESTION")
            eval_summary = parsed.get("evaluation_summary", "Answer received and evaluated.")
            new_diff = parsed.get("new_difficulty", current_diff)
            category = parsed.get("next_question_category", "TECHNICAL")
            q_text = parsed.get("next_question_text", "Could you elaborate further on how you optimize performance in this setup?")
            context = parsed.get("next_question_context", "Adaptive interview progression")
            
            next_q = {
                "id": f"Q-{uuid.uuid4().hex[:6].upper()}",
                "text": q_text,
                "category": category,
                "difficulty": new_diff,
                "context": context,
                "timestamp": _get_timestamp_str()
            }
            
            # Format Activity Stream Event
            events = [
                {
                    "timestamp": _get_timestamp_str(),
                    "event": "Answer Evaluated",
                    "details": eval_summary
                }
            ]
            
            if new_diff != current_diff:
                events.append({
                    "timestamp": _get_timestamp_str(),
                    "event": "Difficulty Adjusted",
                    "details": f"Shifted from {current_diff.upper()} to {new_diff.upper()}"
                })
                
            if new_phase != current_phase:
                events.append({
                    "timestamp": _get_timestamp_str(),
                    "event": "Phase Transition",
                    "details": f"Advanced to {new_phase.replace('_', ' ').title()}"
                })
                
            events.append({
                "timestamp": _get_timestamp_str(),
                "event": f"Question Generated [{category}]",
                "details": f"Difficulty: {new_diff.upper()}"
            })
            
            return {
                "evaluation": eval_summary,
                "decision": decision,
                "new_difficulty": new_diff,
                "new_phase": new_phase,
                "next_question": next_q,
                "events": events
            }
        except Exception as e:
            print(f"[InterviewEngine] AI Evaluation error: {e}, using heuristic adaptive fallback.")

    # Fallback Heuristic Adaptive Evaluator
    return _fallback_adaptive_evaluator(session, candidate_answer, new_phase, current_diff)

def _fallback_adaptive_evaluator(
    session: Dict[str, Any],
    candidate_answer: str,
    new_phase: str,
    current_diff: str
) -> Dict[str, Any]:
    resume = session.get("resume_data", {})
    jd = session.get("job_description_data", {})
    domain = session.get("domain", "Software Engineering")
    projects = resume.get("projects", [])
    skills = resume.get("skills", ["System Architecture", "API Design", "Performance Optimization"])
    jd_skills = jd.get("required_skills", ["Core Principles", "Scalability", "Testing"])
    
    ans_words = len(candidate_answer.split())
    
    # Adaptive heuristic rules
    if ans_words >= 45:
        decision = "INCREASE_DIFFICULTY" if current_diff == "medium" else "FOLLOW_UP"
        new_diff = "hard" if current_diff == "medium" else current_diff
        eval_summary = "Thorough response with good technical elaboration."
    elif ans_words >= 15:
        decision = "FOLLOW_UP"
        new_diff = current_diff
        eval_summary = "Adequate response, probing deeper into technical tradeoffs."
    else:
        decision = "DECREASE_DIFFICULTY"
        new_diff = "easy"
        eval_summary = "Brief answer, steering toward fundamental architectural concepts."

    # Select contextual question based on phase
    if new_phase == "cv_questions" and projects:
        proj = projects[0].get("title", "your system")
        category = "CV"
        q_text = f"In your work with {proj}, what was the most challenging concurrency or scalability bottleneck you encountered, and how did you resolve it?"
    elif new_phase == "domain_questions":
        target_skill = jd_skills[min(len(jd_skills)-1, 1)] if jd_skills else "Microservices"
        category = "DOMAIN"
        q_text = f"Regarding {target_skill} within {domain}: how do you approach fault tolerance, error recovery, and data consistency in production environments?"
    elif new_phase == "behavioral":
        category = "BEHAVIORAL"
        q_text = "Can you describe a situation where you had a strong technical disagreement with a teammate or lead regarding architectural design? How did you reach alignment?"
    else:
        category = "TECHNICAL"
        q_text = f"When designing high-throughput services in {domain}, how do you balance database read/write latency against cache invalidation complexity?"

    next_q = {
        "id": f"Q-{uuid.uuid4().hex[:6].upper()}",
        "text": q_text,
        "category": category,
        "difficulty": new_diff,
        "context": f"Phase {new_phase} technical inquiry",
        "timestamp": _get_timestamp_str()
    }
    
    events = [
        {
            "timestamp": _get_timestamp_str(),
            "event": "Answer Evaluated",
            "details": eval_summary
        },
        {
            "timestamp": _get_timestamp_str(),
            "event": f"Question Generated [{category}]",
            "details": f"Difficulty: {new_diff.upper()}"
        }
    ]

    return {
        "evaluation": eval_summary,
        "decision": decision,
        "new_difficulty": new_diff,
        "new_phase": new_phase,
        "next_question": next_q,
        "events": events
    }
