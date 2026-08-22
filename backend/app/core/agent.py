import time
import os
import re
from pydantic import BaseModel
from typing import List, Optional, Any, Dict, Callable, Awaitable
from google.genai import types

from app.config import settings
from app.core.speech_service import detect_language, detect_target_language
from app.core.tools import launch_target, search_web, play_youtube, get_system_stats, execute_gui_action, send_email
from app.core.email_tool import parse_email_command, validate_email_format, send_email as send_email_gmail
from app.core.calendar_tool import parse_calendar_command, check_calendar, create_event, delete_event
from app.core.reminder_service import parse_reminder_command, create_reminder, list_reminders, cancel_reminder
from app.core.orchestrator import run_react_loop
from app.core.rag import rag_store
from app.core.guardrails import evaluate_guardrails
from app.core.llm_provider import generate_multimodal_content

class AgentResponse(BaseModel):
    reply_text: str
    language: str
    confidence: float
    intent: str
    actions_executed: List[Dict[str, Any]]
    steps: List[Dict[str, Any]] = []
    needs_confirmation: bool = False
    confirmation_reason: Optional[str] = None
    citations: List[str] = []
    latency_ms: float
    token_usage: Dict[str, int] = {}
    task_id: Optional[str] = None

VOCALIS_PERSONA = (
    "You are Vocalis AI, a cutting-edge multimodal voice & vision operating system. "
    "You are intelligent, concise, highly capable, and sleek in tone. "
    "Address the user politely (or as Sir/Ma'am if appropriate). "
    "Keep voice responses natural, crisp, and direct (1-3 sentences max). "
    "Do NOT output internal thinking blocks, chain-of-thought, or <think> tags. "
    "For simple identity or status questions (e.g. 'who are you', 'who created you'), answer directly in 1-2 short sentences without fluff. "
    "When a user asks about what is on their screen or camera, analyze the provided visual frame in detail. "
    "You can execute GUI actions to click, type, press hotkeys, or scroll based on visual grounding. "
    "If you need to perform an action on the screen, append a special tag at the very end of your response: "
    "For clicking: '[GUI_ACTION: click, x, y]' (estimate absolute pixel coordinates based on standard 1920x1080 display). "
    "For typing text: '[GUI_ACTION: type, text_to_type]'. "
    "For key combinations: '[GUI_ACTION: hotkey, key1, key2]'. "
    "For scrolling: '[GUI_ACTION: scroll, amount]' (positive for up, negative for down). "
    "Only output ONE action per turn."
)

_client = None
_pending_action: Optional[Dict[str, Any]] = None

def get_genai_client():
    global _client
    if _client is None and settings.GEMINI_API_KEY:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client

async def process_turn(
    user_query: str,
    image_bytes: Optional[bytes] = None,
    client_lang: Optional[str] = None,
    allow_actions: bool = True,
    max_tokens: Optional[int] = None,
    on_step_update: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
) -> AgentResponse:
    global _pending_action
    start_time = time.time()
    q = user_query.strip()
    detected_lang = client_lang or detect_language(q)
    target_lang = detect_target_language(q) or detected_lang

    actions_executed = []
    citations = []
    confidence = 0.95
    intent = "general_ai"
    needs_confirmation = False
    confirmation_reason = None
    reply_text = ""

    # Check for direct local tool triggers if no image is attached
    if not image_bytes:
        q_lower = q.lower()

        # Handle explicit authorization of pending actions
        if (
            q_lower == "execute authorized action"
            or q_lower.startswith("execute authorized")
            or q_lower in ["confirm", "authorize", "authorize action", "yes send it", "send it", "approve", "proceed", "yes, send it", "yes send", "confirm create", "yes schedule", "schedule it"]
        ):
            if _pending_action:
                pending = _pending_action
                _pending_action = None
                act_type = pending.get("action")
                args = pending.get("args", {})
                if act_type == "send_email":
                    intent = "send_email"
                    res = send_email_gmail(to=args.get("to"), subject=args.get("subject"), body=args.get("body"))
                    actions_executed.append(res)
                    if res.get("status") == "success":
                        reply_text = f"Email successfully sent to {args.get('to')}."
                    else:
                        reply_text = f"Failed to send email: {res.get('message')}"
                elif act_type in ("create_event", "calendar_create"):
                    intent = "calendar_create"
                    res = create_event(
                        title=args.get("title", "Meeting"),
                        start_time=args.get("start_time", ""),
                        end_time=args.get("end_time"),
                        attendees=args.get("attendees"),
                        description=args.get("description"),
                        duration_minutes=args.get("duration_minutes", 30)
                    )
                    actions_executed.append(res)
                    if res.get("status") == "success":
                        reply_text = res.get("message", f"Calendar event '{args.get('title')}' created.")
                    else:
                        reply_text = f"Failed to create calendar event: {res.get('message')}"
                elif act_type in ("delete_event", "calendar_delete"):
                    intent = "calendar_delete"
                    res = delete_event(event_id=args.get("event_id", ""))
                    actions_executed.append(res)
                    if res.get("status") == "success":
                        reply_text = res.get("message", "Calendar event deleted.")
                    else:
                        reply_text = f"Failed to delete calendar event: {res.get('message')}"
                elif act_type == "launch":
                    intent = "app_launch"
                    res = launch_target(args.get("target", ""))
                    actions_executed.append(res)
                    reply_text = f"Opened {args.get('target', '')}."
            else:
                intent = "action_authorization"
                reply_text = "No pending action awaiting authorization."
        elif q_lower.startswith("open ") or q_lower.startswith("launch ") or q_lower.startswith("kholo "):
            target = q_lower.replace("open ", "").replace("launch ", "").replace("kholo ", "").strip()
            
            # Check for secondary compound action (e.g. "open notepad and write hello")
            sub_actions = re.split(r'\s+(?:and\s+(?:then\s+)?|aur\s+|phir\s+)', target, maxsplit=1)
            primary_target = sub_actions[0].strip()
            secondary_action = sub_actions[1].strip() if len(sub_actions) > 1 else None

            intent = "app_launch"
            safe, reason = evaluate_guardrails(intent, {"action": "launch", "target": primary_target}, confidence)
            if safe and allow_actions:
                res = launch_target(primary_target)
                actions_executed.append(res)
                reply_text = f"Opening {primary_target}."

                # If secondary action is typing/writing
                if secondary_action and (secondary_action.startswith("write ") or secondary_action.startswith("type ") or secondary_action.startswith("likho ")):
                    text_to_type = re.sub(r'^(write|type|likho)\s+', '', secondary_action, flags=re.I).strip()
                    if text_to_type:
                        time.sleep(0.8)  # Wait for window focus
                        type_res = execute_gui_action("type", text=text_to_type)
                        actions_executed.append(type_res)
                        reply_text = f"Opened {primary_target} and entered your text."
                elif secondary_action and (secondary_action.startswith("search ") or secondary_action.startswith("look for ") or secondary_action.startswith("searching ")):
                    search_term = re.sub(r'^(search|searching|look for|khojo|dhundho)\s+(for\s+)?', '', secondary_action, flags=re.I).strip()
                    if search_term:
                        search_res = search_web(search_term)
                        actions_executed.append(search_res)
                        reply_text = f"Opened {primary_target} and searched for {search_term}."
                elif secondary_action and (secondary_action.startswith("send ") or secondary_action.startswith("email ") or secondary_action.startswith("mail ")):
                    email_body = None
                    recipient = None
                    
                    send_match = re.search(r'^send\s+(.+?)\s+to\s+(\w+)', secondary_action, re.I)
                    if send_match:
                        email_body = send_match.group(1).strip()
                        recipient = send_match.group(2).strip()
                    else:
                        saying_match = re.search(r'^(?:email|mail)\s+(?:to\s+)?(\w+)\s+saying\s+(.+)', secondary_action, re.I)
                        if saying_match:
                            recipient = saying_match.group(1).strip()
                            email_body = saying_match.group(2).strip()
                        else:
                            fallback_match = re.search(r'^(?:email|mail)\s+(?:to\s+)?(\w+)(?:\s+(.+))?', secondary_action, re.I)
                            if fallback_match:
                                recipient = fallback_match.group(1).strip()
                                email_body = fallback_match.group(2).strip() if fallback_match.group(2) else "Hello"

                    if recipient and email_body:
                        email_res = send_email(recipient, email_body)
                        actions_executed.append(email_res)
                        if email_res.get("status") == "success":
                            reply_text = f"Opened {primary_target} and drafted email to {email_res.get('recipient')}."
                        else:
                            reply_text = f"Opened {primary_target}, but email draft failed: {email_res.get('message')}."
            else:
                _pending_action = {"action": "launch", "args": {"target": primary_target}}
                needs_confirmation = not safe
                confirmation_reason = reason
                reply_text = f"Ready to open {primary_target}. Awaiting confirmation."
        elif q_lower.startswith("play ") or q_lower.startswith("bajao ") or "on youtube" in q_lower:
            intent = "youtube"
            if allow_actions:
                res = play_youtube(q)
                actions_executed.append(res)
            reply_text = f"Playing {q} on YouTube."
        elif q_lower.startswith("search for ") or q_lower.startswith("google "):
            term = q_lower.replace("search for ", "").replace("google ", "").strip()
            intent = "web_search"
            if allow_actions:
                res = search_web(term)
                actions_executed.append(res)
            reply_text = f"Searching for {term}."
        elif "system stats" in q_lower or "cpu usage" in q_lower or "ram usage" in q_lower or "battery" in q_lower:
            intent = "system_telemetry"
            stats = get_system_stats()
            actions_executed.append({"status": "success", "action": "system_stats", "data": stats})
            reply_text = f"CPU is at {stats['cpu_percent']}%, and RAM usage is {stats['ram_percent']}% ({stats['ram_used_gb']}GB of {stats['ram_total_gb']}GB)."
        elif (
            q_lower.startswith("send a mail")
            or q_lower.startswith("send an email")
            or q_lower.startswith("send mail")
            or q_lower.startswith("send email")
            or q_lower.startswith("email ")
            or (("@" in q_lower or "mail" in q_lower) and ("send" in q_lower or "email" in q_lower))
        ):
            intent = "send_email"
            parsed = parse_email_command(q)
            to_addr = parsed.get("to")
            subject = parsed.get("subject") or "Message from Vocalis AI"
            body = parsed.get("body") or ""

            if not to_addr:
                confidence = 0.90
                reply_text = "Who would you like me to send the email to? Please provide the recipient's email address."
            elif not validate_email_format(to_addr):
                confidence = 0.85
                reply_text = f"The recipient email address '{to_addr}' is invalid. Please provide a valid email format."
            else:
                safe, reason = evaluate_guardrails(
                    intent="send_email",
                    action_data={"to": to_addr, "subject": subject, "body": body},
                    confidence=confidence,
                    tool_name="send_email",
                    tool_args={"to": to_addr, "subject": subject, "body": body}
                )
                _pending_action = {"action": "send_email", "args": {"to": to_addr, "subject": subject, "body": body}}
                needs_confirmation = not safe
                confirmation_reason = reason
                reply_text = f"Ready to send email to {to_addr} with subject '{subject}'. Awaiting your confirmation."
        
        # Calendar Management Intent
        elif any(p in q_lower for p in ["calendar", "schedule a meeting", "schedule meeting", "am i free", "what's on my schedule", "whats on my schedule", "my schedule", "book a meeting", "cancel meeting", "cancel my meeting"]):
            parsed_cal = parse_calendar_command(q)
            cal_action = parsed_cal.get("action")
            if cal_action == "check":
                intent = "calendar_check"
                res = check_calendar(date_range=parsed_cal.get("date_range"))
                actions_executed.append(res)
                reply_text = res.get("message", "Checked your calendar.")
                if res.get("events"):
                    event_lines = []
                    for ev in res["events"][:5]:
                        start_str = ev.get("start", "")
                        summary = ev.get("summary", "Event")
                        event_lines.append(f"• {summary} ({start_str})")
                    reply_text += "\n" + "\n".join(event_lines)
            elif cal_action == "create":
                intent = "calendar_create"
                safe, reason = evaluate_guardrails(
                    intent="create_event",
                    action_data=parsed_cal,
                    confidence=confidence,
                    tool_name="create_event",
                    tool_args=parsed_cal
                )
                _pending_action = {"action": "create_event", "args": parsed_cal}
                needs_confirmation = not safe
                confirmation_reason = reason
                reply_text = f"Ready to schedule '{parsed_cal.get('title')}' for {parsed_cal.get('start_time')}. Awaiting your confirmation."
            elif cal_action == "delete":
                intent = "calendar_delete"
                safe, reason = evaluate_guardrails(
                    intent="delete_event",
                    action_data=parsed_cal,
                    confidence=confidence,
                    tool_name="delete_event",
                    tool_args=parsed_cal
                )
                _pending_action = {"action": "delete_event", "args": parsed_cal}
                needs_confirmation = not safe
                confirmation_reason = reason
                reply_text = f"Ready to cancel calendar event. Awaiting your confirmation."

        # Reminders & Task Management Intent (Local only, no external API)
        elif (
            q_lower.startswith("remind me")
            or q_lower.startswith("set a reminder")
            or q_lower.startswith("set reminder")
            or "reminder" in q_lower
        ):
            parsed_rem = parse_reminder_command(q)
            rem_action = parsed_rem.get("action")
            if rem_action == "list":
                intent = "list_reminders"
                res = list_reminders(status_filter="pending")
                actions_executed.append(res)
                reply_text = res.get("message", "Retrieved your reminders.")
                if res.get("reminders"):
                    rem_lines = [f"• #{r['id']}: {r['text']} (Due: {r['due_time']})" for r in res["reminders"][:5]]
                    reply_text += "\n" + "\n".join(rem_lines)
            elif rem_action == "cancel":
                intent = "cancel_reminder"
                rem_id = parsed_rem.get("reminder_id")
                if rem_id:
                    res = cancel_reminder(reminder_id=rem_id)
                    actions_executed.append(res)
                    reply_text = res.get("message", f"Cancelled reminder #{rem_id}.")
                else:
                    res = list_reminders(status_filter="pending")
                    actions_executed.append(res)
                    if res.get("reminders"):
                        rem_to_cancel = res["reminders"][0]
                        c_res = cancel_reminder(reminder_id=rem_to_cancel["id"])
                        actions_executed.append(c_res)
                        reply_text = f"Cancelled reminder #{rem_to_cancel['id']}: '{rem_to_cancel['text']}'."
                    else:
                        reply_text = "No active reminders found to cancel."
            else:
                # Create reminder (local only, no confirmation needed)
                intent = "create_reminder"
                res = create_reminder(text=parsed_rem.get("text", "Reminder"), due_time=parsed_rem.get("due_time", "in 1 hour"))
                actions_executed.append(res)
                if res.get("status") == "success":
                    reply_text = res.get("message", f"Reminder set: '{parsed_rem.get('text')}'.")
                else:
                    reply_text = f"Failed to set reminder: {res.get('message')}"

    # If already handled by deterministic tools
    if reply_text:
        latency = max(0.1, round((time.time() - start_time) * 1000, 2))
        return AgentResponse(
            reply_text=reply_text,
            language=target_lang,
            confidence=confidence,
            intent=intent,
            actions_executed=actions_executed,
            needs_confirmation=needs_confirmation,
            confirmation_reason=confirmation_reason,
            citations=citations,
            latency_ms=latency,
            token_usage={"prompt_tokens": 0, "response_tokens": 0}
        )

    # Retrieval Grounding (RAG)
    rag_docs = rag_store.search(q, top_k=2)
    rag_context = ""
    if rag_docs:
        rag_context = "\n\nRelevant Grounded Knowledge:\n" + "\n".join(
            [f"- [{d['title']}]: {d['content']}" for d in rag_docs]
        )
        citations = [d['title'] for d in rag_docs]

    # Check if query requests multi-step / tool tasks
    is_agentic_task = any(w in q.lower() for w in [
        "file", "script", "create", "write", "read", "delete", "edit",
        "terminal", "run", "code", "search", "scrape", "directory", "list", "test", "folder"
    ])

    if is_agentic_task and allow_actions and (settings.GEMINI_API_KEY or settings.GROQ_API_KEY):
        react_res = await run_react_loop(
            user_query=q,
            image_bytes=image_bytes,
            client_lang=target_lang,
            allow_actions=allow_actions,
            on_step_update=on_step_update
        )
        latency = max(0.1, round((time.time() - start_time) * 1000, 2))
        return AgentResponse(
            reply_text=react_res.final_text,
            language=target_lang,
            confidence=0.98 if react_res.success else 0.60,
            intent="react_orchestrator",
            actions_executed=react_res.actions_executed,
            steps=react_res.steps,
            needs_confirmation=react_res.needs_confirmation,
            confirmation_reason=react_res.confirmation_reason,
            citations=citations,
            latency_ms=latency,
            token_usage={"prompt_tokens": len(react_res.steps) * 150, "response_tokens": 100},
            task_id=react_res.task_id
        )

    # Multimodal / LLM processing with Gemini-Groq failover
    if not settings.GEMINI_API_KEY and not settings.GROQ_API_KEY:
        # Fallback without API keys
        return AgentResponse(
            reply_text="Api has been exhausted, plz try after sometime",
            language=target_lang,
            confidence=0.60,
            intent="offline_fallback",
            actions_executed=[],
            latency_ms=max(0.1, round((time.time() - start_time) * 1000, 2))
        )

    try:
        lang_prompt = f" Respond in {target_lang}."
        if target_lang == 'hi':
            lang_prompt = " Respond ONLY in Hindi (Devanagari script)."
        elif target_lang == 'bn':
            lang_prompt = " Respond ONLY in Bengali (Bengali script)."

        full_prompt = f"{VOCALIS_PERSONA}\n{lang_prompt}{rag_context}\n\nUser Question: {q}"

        # Check if query is a simple question (identity, greeting, simple status)
        is_simple_query = any(pattern in q.lower() for pattern in [
            "who are you", "who r u", "what is your name", "what's your name",
            "who made you", "who created you", "hi", "hello", "hey", "how are you"
        ])
        effective_max_tokens = 100 if is_simple_query else max_tokens

        reply_text, provider = await generate_multimodal_content(
            prompt_text=full_prompt,
            image_bytes=image_bytes,
            system_instruction=None,
            max_tokens=effective_max_tokens
        )
        confidence = 0.96

        # Strip any internal thinking blocks (<think>...</think>) if output by model
        reply_text = re.sub(r'<think>.*?</think>', '', reply_text, flags=re.DOTALL).strip()
        reply_text = re.sub(r'</?think>', '', reply_text).strip()


        # Parse GUI actions from response
        action_match = re.search(r'\[GUI_ACTION:\s*([^\]]+)\]', reply_text)
        if action_match and allow_actions:
            action_parts = [p.strip() for p in action_match.group(1).split(",")]
            if action_parts:
                action_type = action_parts[0]
                if action_type == "click" and len(action_parts) >= 3:
                    try:
                        x = int(action_parts[1])
                        y = int(action_parts[2])
                        res = execute_gui_action("click", x=x, y=y)
                        actions_executed.append(res)
                    except ValueError:
                        pass
                elif action_type == "type" and len(action_parts) >= 2:
                    text_val = action_parts[1]
                    res = execute_gui_action("type", text=text_val)
                    actions_executed.append(res)
                elif action_type == "hotkey" and len(action_parts) >= 2:
                    keys = action_parts[1:]
                    res = execute_gui_action("hotkey", keys=keys)
                    actions_executed.append(res)
                elif action_type == "scroll" and len(action_parts) >= 2:
                    amt = action_parts[1]
                    res = execute_gui_action("scroll", text=amt)
                    actions_executed.append(res)

    except Exception as e:
        reply_text = f"An issue occurred while consulting the intelligence engine: {str(e)}"
        confidence = 0.50

    latency = max(0.1, round((time.time() - start_time) * 1000, 2))
    return AgentResponse(
        reply_text=reply_text,
        language=target_lang,
        confidence=confidence,
        intent=intent,
        actions_executed=actions_executed,
        needs_confirmation=needs_confirmation,
        confirmation_reason=confirmation_reason,
        citations=citations,
        latency_ms=latency,
        token_usage={"prompt_tokens": 150, "response_tokens": 50}
    )
