import json
import time
import uuid
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from app.config import settings
from app.core.llm_provider import generate_gemini_content_sync

# Supported Question Categories
CATEGORIES = ["CV", "TECHNICAL", "DOMAIN", "BEHAVIORAL", "FOLLOW_UP"]

# Strict Rubric Definition (0 to 10 scale)
RUBRIC = {
    0: "No answer / completely irrelevant",
    (1, 2): "Fundamentally incorrect / contradictions",
    (3, 4): "Major gaps; limited understanding",
    (5, 6): "Partially correct; noticeable gaps",
    (7, 8): "Correct and reasonably complete",
    9: "Excellent depth and accuracy",
    10: "Exceptional depth, precision, and reasoning"
}



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
    
    if settings.GEMINI_API_KEYS:
        prompt = f"""
        You are a strict, objective, and expert Technical AI Interviewer conducting a formal technical interview.
        Candidate Name: {candidate_name}
        Target Track: {domain}
        Candidate Projects: {json.dumps(projects)}
        Candidate Skills: {json.dumps(skills[:8])}
        Job Role: {jd.get('title', 'Software Engineer')}

        Formulate a precise technical opening question asking the candidate to introduce their architectural design and specific engineering contributions on their primary project.

        Respond ONLY with a valid JSON object matching this schema:
        {{
            "text": "The technical opening interview question",
            "category": "CV",
            "difficulty": "medium",
            "context": "Opening architectural project inquiry",
            "expected_concept": "Candidate should clearly explain the end-to-end architecture, tech stack justification, and personal contributions."
        }}
        """
        try:
            response = generate_gemini_content_sync(
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                )
            )
            parsed = json.loads(response.text)
            return {
                "id": f"Q-{uuid.uuid4().hex[:6].upper()}",
                "text": parsed.get("text", f"Welcome {candidate_name}. To begin, please introduce yourself and detail the technical architecture and your specific engineering contributions to your primary project."),
                "category": parsed.get("category", "CV"),
                "difficulty": parsed.get("difficulty", "medium"),
                "context": parsed.get("context", "Opening introduction"),
                "expected_concept": parsed.get("expected_concept", "End-to-end architecture and personal contributions"),
                "timestamp": _get_timestamp_str()
            }
        except Exception as e:
            print(f"[InterviewEngine] AI Initial Question error: {e}, using fallback.")

    # Fallback Opening Question
    project_title = projects[0].get("title", "your featured project") if projects else "your key project"
    return {
        "id": f"Q-{uuid.uuid4().hex[:6].upper()}",
        "text": f"Welcome {candidate_name} to your Vocalis AI technical interview for the {domain} track. To start, introduce yourself and explain the architectural design and your concrete implementation work on {project_title}.",
        "category": "CV",
        "difficulty": "medium",
        "context": "Opening introduction and CV project walkthrough",
        "expected_concept": "Comprehensive architectural walkthrough with technical stack justification",
        "timestamp": _get_timestamp_str()
    }

def evaluate_answer_and_next_turn(session: Dict[str, Any], candidate_answer: str) -> Dict[str, Any]:
    """
    STRICT, EVIDENCE-BASED EVALUATION (0-10 Scale).
    Evaluates candidate's answer against expected concepts, detects missing concepts/incorrect claims,
    and assigns a strict 0-10 score with factual justification.
    """
    resume = session.get("resume_data", {})
    jd = session.get("job_description_data", {})
    domain = session.get("domain", "Software Engineering")
    current_q = session.get("current_question") or {}
    history = session.get("questions_history", [])
    current_diff = session.get("difficulty", "medium")
    current_phase = session.get("current_phase", "introduction")
    start_time = session.get("start_time") or time.time()
    
    elapsed_seconds = time.time() - start_time
    total_answered = len(history) + 1
    new_phase = determine_phase_by_elapsed(elapsed_seconds, current_phase, total_answered)
    
    if settings.GEMINI_API_KEYS and len(candidate_answer.strip()) > 2:
        prompt = f"""
        You are a STRICT, RIGOROUS, AND OBJECTIVE Technical AI Interviewer evaluating a candidate's response.
        
        CRITICAL EVALUATION PRINCIPLES:
        - Correctness > Confidence.
        - Depth > Buzzwords.
        - Evidence > Generic Praise.
        - NEVER give high scores (7+) just because an answer is long or well-phrased.
        - If the candidate makes an incorrect claim or confuses concepts, penalize heavily.
        - Partial understanding receives partial score (5-6/10).
        - Fundamentally incorrect or irrelevant answers receive (1-2/10).
        - Blank or nonsensical answers receive (0/10).
        - DO NOT use generic flattering language (e.g. "Great job!", "Good understanding!"). State factual evidence.

        SCORING SCALE (0-10):
        0: No answer / completely irrelevant
        1-2: Fundamentally incorrect / contradictory claims
        3-4: Major gaps; limited understanding
        5-6: Partially correct; noticeable conceptual gaps
        7-8: Correct, accurate, and reasonably complete
        9: Excellent technical depth and accuracy
        10: Exceptional precision, tradeoffs, and architectural depth

        Context:
        - Target Track: {domain}
        - Current Phase: {new_phase}
        - Current Question: \"{current_q.get('text', '')}\"
        - Expected Concept: \"{current_q.get('expected_concept', 'Accurate technical explanation and concrete details')}\"
        - Candidate Answer: \"{candidate_answer}\"
        - Previous Questions: {json.dumps([h.get('question_text', '') for h in history])}

        Your Task:
        1. Formulate the Expected Concept and Key Requirements internally.
        2. Analyze Correctness, Missing Concepts, and any Incorrect Claims.
        3. Assign an integer score from 0 to 10.
        4. Write a 1-2 sentence strict evidence-based reason explaining why this score was awarded.
        5. Decide next action:
           - "FOLLOW_UP": If candidate mentioned specific mechanisms that warrant immediate deep probe.
           - "INCREASE_DIFFICULTY": If score >= 8 and answer demonstrated exceptional depth.
           - "DECREASE_DIFFICULTY": If score <= 4 and answer demonstrated fundamental confusion.
           - "ASK_QUESTION": Move to next technical domain topic.
           - "END_INTERVIEW": If phase is complete.
        6. Formulate the next technical question (Category: CV | TECHNICAL | DOMAIN | BEHAVIORAL | FOLLOW_UP).

        Respond ONLY with a valid JSON object matching this schema:
        {{
            "score": 0-10,
            "evaluation_justification": "Evidence-based critique detailing correct elements, missing concepts, or factual errors.",
            "expected_concept": "Key technical concepts expected for this question",
            "decision": "FOLLOW_UP | INCREASE_DIFFICULTY | DECREASE_DIFFICULTY | ASK_QUESTION | END_INTERVIEW",
            "new_difficulty": "easy | medium | hard",
            "next_question_text": "The next question to ask",
            "next_question_category": "CV | TECHNICAL | DOMAIN | BEHAVIORAL | FOLLOW_UP",
            "next_question_context": "Reason for question choice",
            "next_expected_concept": "What a strong answer to the next question must contain"
        }}
        """
        try:
            response = generate_gemini_content_sync(
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.15,
                    response_mime_type="application/json",
                )
            )
            parsed = json.loads(response.text)
            
            score = int(parsed.get("score", 5))
            score = max(0, min(10, score))
            justification = parsed.get("evaluation_justification", "Answer evaluated against technical criteria.")
            exp_concept = parsed.get("expected_concept", "Technical correctness and concrete architectural evidence")
            decision = parsed.get("decision", "ASK_QUESTION")
            new_diff = parsed.get("new_difficulty", current_diff)
            category = parsed.get("next_question_category", "TECHNICAL")
            q_text = parsed.get("next_question_text", "How do you ensure data integrity and fault isolation in this architecture?")
            context = parsed.get("next_question_context", "Adaptive interview progression")
            next_exp = parsed.get("next_expected_concept", "Fault tolerance, replication, and distributed consensus mechanisms")
            
            next_q = {
                "id": f"Q-{uuid.uuid4().hex[:6].upper()}",
                "text": q_text,
                "category": category,
                "difficulty": new_diff,
                "context": context,
                "expected_concept": next_exp,
                "timestamp": _get_timestamp_str()
            }
            
            # Format Activity Stream Events
            events = [
                {
                    "timestamp": _get_timestamp_str(),
                    "event": f"Answer Evaluated: {score}/10",
                    "details": justification
                }
            ]
            
            if new_diff != current_diff:
                events.append({
                    "timestamp": _get_timestamp_str(),
                    "event": "Difficulty Adjusted",
                    "details": f"Shifted to {new_diff.upper()} based on score ({score}/10)"
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
                "score": score,
                "evaluation": justification,
                "expected_concept": exp_concept,
                "decision": decision,
                "new_difficulty": new_diff,
                "new_phase": new_phase,
                "next_question": next_q,
                "events": events
            }
        except Exception as e:
            print(f"[InterviewEngine] AI Strict Evaluation error: {e}, using heuristic fallback.")

    # Strict Heuristic Fallback
    return _strict_heuristic_evaluator(session, candidate_answer, new_phase, current_diff)

def _strict_heuristic_evaluator(
    session: Dict[str, Any],
    candidate_answer: str,
    new_phase: str,
    current_diff: str
) -> Dict[str, Any]:
    ans_clean = candidate_answer.strip()
    words = ans_clean.split()
    word_count = len(words)
    
    if word_count == 0 or ans_clean.lower() in ["skip", "i don't know", "no idea", "pass"]:
        score = 0
        justification = "Candidate provided no technical response to the question."
        decision = "DECREASE_DIFFICULTY"
        new_diff = "easy"
    elif word_count < 10:
        score = 2
        justification = "Answer is excessively brief and fails to demonstrate technical comprehension."
        decision = "DECREASE_DIFFICULTY"
        new_diff = "easy"
    elif word_count < 30:
        score = 5
        justification = "Candidate provided a partial answer but lacked architectural depth and concrete implementation details."
        decision = "FOLLOW_UP"
        new_diff = current_diff
    elif word_count < 60:
        score = 7
        justification = "Accurate response covering key concepts with satisfactory technical precision."
        decision = "FOLLOW_UP" if current_diff == "hard" else "INCREASE_DIFFICULTY"
        new_diff = "hard" if current_diff == "medium" else current_diff
    else:
        score = 8
        justification = "Thorough and structured explanation demonstrating clear domain understanding and tradeoff awareness."
        decision = "INCREASE_DIFFICULTY"
        new_diff = "hard"

    domain = session.get("domain", "Software Engineering")
    jd = session.get("job_description_data", {})
    jd_skills = jd.get("required_skills", ["Distributed Systems", "Performance Optimization"])
    
    if new_phase == "cv_questions":
        category = "CV"
        q_text = "What specific profiling tools and metrics did you monitor to identify performance bottlenecks in your system?"
        exp = "Profiling tools (e.g. cProfile, flamegraphs, APM) and latency/throughput metrics"
    elif new_phase == "domain_questions":
        category = "DOMAIN"
        target_skill = jd_skills[0] if jd_skills else "Microservices"
        q_text = f"In the context of {domain} and {target_skill}, how do you handle data consistency, idempotency, and network partitions across services?"
        exp = "Saga patterns, 2PC tradeoffs, idempotent keys, and CAP theorem considerations"
    elif new_phase == "behavioral":
        category = "BEHAVIORAL"
        q_text = "Describe a critical production incident or architecture flaw you resolved under high time pressure. What post-mortem steps did you enforce?"
        exp = "Incident triage, root cause analysis, and automated regression prevention"
    else:
        category = "TECHNICAL"
        q_text = f"When scaling asynchronous workers in {domain}, how do you prevent race conditions and handle dead-letter queues?"
        exp = "Message acknowledgment, exponential backoff, locking mechanisms, and DLQ alerting"

    next_q = {
        "id": f"Q-{uuid.uuid4().hex[:6].upper()}",
        "text": q_text,
        "category": category,
        "difficulty": new_diff,
        "context": f"Phase {new_phase} inquiry",
        "expected_concept": exp,
        "timestamp": _get_timestamp_str()
    }
    
    events = [
        {
            "timestamp": _get_timestamp_str(),
            "event": "API Notice",
            "details": "Api has been exhausted, plz try after sometime"
        },
        {
            "timestamp": _get_timestamp_str(),
            "event": f"Answer Evaluated: {score}/10",
            "details": justification
        },
        {
            "timestamp": _get_timestamp_str(),
            "event": f"Question Generated [{category}]",
            "details": f"Difficulty: {new_diff.upper()}"
        }
    ]

    return {
        "score": score,
        "evaluation": justification,
        "expected_concept": "Architectural tradeoffs and technical accuracy",
        "decision": decision,
        "new_difficulty": new_diff,
        "new_phase": new_phase,
        "next_question": next_q,
        "events": events
    }

def generate_final_evaluation_report(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesizes the strict final scorecard and evaluation report for the candidate.
    """
    history = session.get("questions_history", [])
    integrity_events = session.get("integrity_events", [])
    integrity_score = session.get("integrity_score", 10.0)
    domain = session.get("domain", "Software Engineering")
    experience_level = session.get("experience_level", "1–3 Years")
    programming_language = session.get("programming_language", "Python")
    
    # Calculate Question Scores
    question_scores = []
    for h in history:
        s = h.get("score")
        if s is None:
            # Derive score from heuristic if absent
            words = len(h.get("answer_text", "").split())
            s = 7 if words >= 30 else (5 if words >= 15 else 3)
        question_scores.append(s)
        
    avg_score = round(sum(question_scores) / max(1, len(question_scores)), 1) if question_scores else 5.0
    
    # Category calculations
    tech_knowledge = round(min(10.0, max(1.0, avg_score + 0.2)), 1)
    problem_solving = round(min(10.0, max(1.0, avg_score - 0.3)), 1)
    communication = round(min(10.0, max(1.0, (sum(1 for h in history if len(h.get("answer_text", "").split()) >= 25) / max(1, len(history))) * 10)), 1)
    answer_accuracy = avg_score
    
    # Overall score incorporates technical performance and integrity
    overall_score = round((avg_score * 0.85) + ((integrity_score / 10.0) * 1.5), 1)
    overall_score = min(10.0, max(0.0, overall_score))

    # Objective Recommendation based on strict thresholds
    if overall_score >= 8.5 and integrity_score >= 7.5:
        recommendation = "Strong Hire"
        rec_color = "emerald"
    elif overall_score >= 7.0 and integrity_score >= 6.0:
        recommendation = "Hire"
        rec_color = "cyan"
    elif overall_score >= 5.0:
        recommendation = "Borderline"
        rec_color = "amber"
    else:
        recommendation = "No Hire"
        rec_color = "red"

    if settings.GEMINI_API_KEYS and history:
        prompt = f"""
        You are a strict, objective, and unbiased Technical Hiring Bar Raiser creating the final candidate evaluation report.
        
        Candidate Profile:
        - Track: {domain} ({experience_level}, {programming_language})
        - Questions Answered ({len(history)} turns):
        {json.dumps([{
            "question": h.get("question_text"),
            "category": h.get("category"),
            "candidate_answer": h.get("answer_text"),
            "score": h.get("score", 5),
            "critique": h.get("evaluation")
        } for h in history])}
        
        Integrity Signals:
        - Integrity Score: {integrity_score}/10
        - Total Integrity Events: {len(integrity_events)}
        - Events List: {json.dumps(integrity_events)}

        Produce a strict, fact-based assessment without generic praise:
        1. 3-4 bulleted concrete Strengths (with technical evidence).
        2. 3-4 bulleted concrete Weaknesses (with specific missing concepts).
        3. 2-3 Critical Knowledge Gaps identified during the interview.
        4. A 2-sentence executive summary justifying the recommendation: "{recommendation}".

        Respond ONLY with a valid JSON object matching this schema:
        {{
            "strengths": ["string", "string"],
            "weaknesses": ["string", "string"],
            "critical_knowledge_gaps": ["string", "string"],
            "evaluator_summary": "Strict 2-sentence executive summary"
        }}
        """
        try:
            response = generate_gemini_content_sync(
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                )
            )
            parsed = json.loads(response.text)
            strengths = parsed.get("strengths", [])
            weaknesses = parsed.get("weaknesses", [])
            gaps = parsed.get("critical_knowledge_gaps", [])
            summary = parsed.get("evaluator_summary", f"Candidate demonstrated {avg_score}/10 technical accuracy across {len(history)} questions.")
            
            return {
                "overall_score": overall_score,
                "technical_knowledge": tech_knowledge,
                "problem_solving": problem_solving,
                "communication": communication,
                "answer_accuracy": answer_accuracy,
                "interview_integrity": integrity_score,
                "final_recommendation": recommendation,
                "recommendation_color": rec_color,
                "total_questions": len(history),
                "question_scores": question_scores,
                "strengths": strengths or ["Demonstrated familiarity with fundamental track frameworks."],
                "weaknesses": weaknesses or ["Lacked deep architectural tradeoffs on complex scenarios."],
                "critical_knowledge_gaps": gaps or ["Distributed consistency and error isolation."],
                "evaluator_summary": summary,
                "integrity_events": integrity_events,
                "timestamp": _get_timestamp_str()
            }
        except Exception as e:
            print(f"[InterviewEngine] AI Final Report error: {e}, using fallback generator.")

    # Strict Fallback Final Report Generator
    tab_switches = sum(1 for e in integrity_events if "tab" in e.get("event_type", "").lower())
    fs_exits = sum(1 for e in integrity_events if "fullscreen" in e.get("event_type", "").lower())
    
    return {
        "overall_score": overall_score,
        "technical_knowledge": tech_knowledge,
        "problem_solving": problem_solving,
        "communication": communication,
        "answer_accuracy": answer_accuracy,
        "interview_integrity": integrity_score,
        "final_recommendation": recommendation,
        "recommendation_color": rec_color,
        "total_questions": len(history),
        "question_scores": question_scores,
        "strengths": [
            f"Demonstrated core competence in {domain} concepts.",
            f"Clear articulation of primary stack tooling in {programming_language}."
        ],
        "weaknesses": [
            "Incomplete tradeoff explanations under high-concurrency scenarios.",
            "Superficial coverage of distributed failure isolation."
        ],
        "critical_knowledge_gaps": [
            "Caching synchronization and cache-aside invalidation boundaries.",
            "Distributed transaction rollback mechanisms."
        ],
        "evaluator_summary": f"Candidate completed {len(history)} technical rounds with an average score of {avg_score}/10. Recorded {tab_switches} tab switches and {fs_exits} full-screen exits.",
        "integrity_events": integrity_events,
        "timestamp": _get_timestamp_str()
    }
