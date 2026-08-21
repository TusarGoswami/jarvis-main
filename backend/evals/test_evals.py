import pytest
import asyncio
from app.core.agent import process_turn
from app.core.speech_service import detect_language, detect_target_language
from app.core.tools import _fuzzy_match, get_system_stats
from app.core.rag import rag_store
from app.core.guardrails import evaluate_guardrails

# ==================== 20-CASE EVALUATION HARNESS ====================

@pytest.mark.asyncio
async def test_01_language_detection_english():
    assert detect_language("What is the system latency?") == "en"

@pytest.mark.asyncio
async def test_02_language_detection_hindi_devanagari():
    assert detect_language("नमस्ते, आप कैसे हैं?") == "hi"

@pytest.mark.asyncio
async def test_03_language_detection_hindi_romanized():
    assert detect_language("kya haal hai bhai batao") == "hi"

@pytest.mark.asyncio
async def test_04_language_detection_bengali_script():
    assert detect_language("আপনি কেমন আছেন?") == "bn"

@pytest.mark.asyncio
async def test_05_language_detection_bengali_romanized():
    assert detect_language("tumi kemon acho bolo") == "bn"

@pytest.mark.asyncio
async def test_06_target_language_override():
    assert detect_target_language("explain quantum computing in hindi") == "hi"
    assert detect_target_language("tell me a joke in bengali") == "bn"

@pytest.mark.asyncio
async def test_07_fuzzy_app_matching():
    match = _fuzzy_match("notepd")
    assert match is not None
    assert match[0] == "notepad"

@pytest.mark.asyncio
async def test_08_fuzzy_site_matching():
    match = _fuzzy_match("ytube")
    assert match is not None or _fuzzy_match("youtub")[0] == "youtube"

@pytest.mark.asyncio
async def test_09_system_telemetry_fields():
    stats = get_system_stats()
    assert "cpu_percent" in stats
    assert "ram_percent" in stats
    assert "ram_used_gb" in stats
    assert "net_sent_mb" in stats

@pytest.mark.asyncio
async def test_10_guardrails_destructive_action_block():
    safe, reason = evaluate_guardrails("system_shutdown", {"action": "system_shutdown"}, 0.99)
    assert safe is False
    assert "requires explicit human authorization" in reason

@pytest.mark.asyncio
async def test_11_guardrails_low_confidence_block():
    safe, reason = evaluate_guardrails("app_launch", {"action": "launch", "target": "unknown"}, 0.45)
    assert safe is False
    assert "below the autonomous execution threshold" in reason

@pytest.mark.asyncio
async def test_12_guardrails_safe_action_allow():
    safe, reason = evaluate_guardrails("app_launch", {"action": "launch", "target": "notepad"}, 0.95)
    assert safe is True
    assert reason is None

@pytest.mark.asyncio
async def test_13_rag_retrieval_vocalis_query():
    docs = rag_store.search("Tell me about Vocalis AI architecture")
    assert len(docs) > 0
    assert "Vocalis AI" in docs[0]["title"] or "Vocalis AI" in docs[0]["content"]

@pytest.mark.asyncio
async def test_14_rag_retrieval_features_query():
    docs = rag_store.search("supported features window switching")
    assert len(docs) > 0
    assert any("features" in d["id"].lower() for d in docs)

@pytest.mark.asyncio
async def test_15_agent_deterministic_app_launch():
    res = await process_turn("open calculator", allow_actions=False)
    assert res.intent == "app_launch"
    assert res.confidence >= 0.90
    assert "calculator" in res.reply_text.lower()

@pytest.mark.asyncio
async def test_16_agent_deterministic_youtube():
    res = await process_turn("play interstellar soundtrack on youtube", allow_actions=False)
    assert res.intent == "youtube"
    assert "interstellar" in res.reply_text.lower()

@pytest.mark.asyncio
async def test_17_agent_deterministic_system_stats():
    res = await process_turn("what is the current cpu usage?", allow_actions=False)
    assert res.intent == "system_telemetry"
    assert "CPU is at" in res.reply_text

@pytest.mark.asyncio
async def test_18_agent_latency_benchmark():
    res = await process_turn("search for latest ai models", allow_actions=False)
    assert res.latency_ms > 0
    # Deterministic local dispatch should be under 500ms
    assert res.latency_ms < 500

@pytest.mark.asyncio
async def test_19_agent_multilingual_response_routing():
    res = await process_turn("aaj ki date kya hai", client_lang="hi", allow_actions=False)
    assert res.language == "hi"

@pytest.mark.asyncio
async def test_20_agent_offline_graceful_degradation():
    res = await process_turn("What is the capital of France?", allow_actions=False)
    assert res.reply_text is not None
    assert res.confidence > 0

# ==================== ADVANCED AGENT & TOOL EVALUATIONS ====================

from app.core.fs_tools import fs_write, fs_read, fs_edit, fs_list, fs_delete, _resolve_safe_path
from app.core.terminal_tool import execute_terminal_command
from app.core.tools_registry import execute_tool, get_tools_prompt_description
from app.core.task_manager import task_manager, TaskState

@pytest.mark.asyncio
async def test_21_sandboxed_fs_write_and_read():
    write_res = fs_write("test_agent.txt", "Line 1: Hello Vocalis\nLine 2: Agentic OS")
    assert write_res["status"] == "success"
    assert write_res["bytes_written"] > 0

    read_res = fs_read("test_agent.txt")
    assert read_res["status"] == "success"
    assert "Hello Vocalis" in read_res["content"]
    assert read_res["lines"] == 2

@pytest.mark.asyncio
async def test_22_sandboxed_fs_edit():
    edit_res = fs_edit("test_agent.txt", "Hello Vocalis", "Hello Autonomous Agent")
    assert edit_res["status"] == "success"

    read_res = fs_read("test_agent.txt")
    assert "Hello Autonomous Agent" in read_res["content"]

@pytest.mark.asyncio
async def test_23_sandboxed_fs_list():
    list_res = fs_list(".")
    assert list_res["status"] == "success"
    assert any(e["name"] == "test_agent.txt" for e in list_res["entries"])

@pytest.mark.asyncio
async def test_24_sandboxed_fs_delete():
    del_res = fs_delete("test_agent.txt")
    assert del_res["status"] == "success"

    read_res = fs_read("test_agent.txt")
    assert read_res["status"] == "error"

@pytest.mark.asyncio
async def test_25_sandboxed_fs_path_traversal_protection():
    with pytest.raises(PermissionError) as exc_info:
        _resolve_safe_path("../../windows/system32/cmd.exe")
    assert "Security sandbox violation" in str(exc_info.value)

@pytest.mark.asyncio
async def test_26_sandboxed_terminal_execution():
    cmd_res = execute_terminal_command("python -c \"print('Vocalis Test Exec')\"")
    assert cmd_res["status"] == "success"
    assert "Vocalis Test Exec" in cmd_res["stdout"]
    assert cmd_res["returncode"] == 0

@pytest.mark.asyncio
async def test_27_sandboxed_terminal_blocked_commands():
    cmd_res = execute_terminal_command("format C:")
    assert cmd_res["status"] == "error"
    assert "Security restriction" in cmd_res["message"]

@pytest.mark.asyncio
async def test_28_tool_registry_dispatch():
    res = await execute_tool("fs_write", {"filepath": "registry_test.txt", "content": "Registry Active"})
    assert res["status"] == "success"
    
    del_res = await execute_tool("fs_delete", {"filepath": "registry_test.txt"})
    assert del_res["status"] == "success"

@pytest.mark.asyncio
async def test_29_task_manager_state_lifecycle():
    task = task_manager.create_task("Analyze test project")
    assert task.state == TaskState.RECEIVED

    task_manager.update_state(task.task_id, TaskState.PLANNING)
    assert task_manager.get_task(task.task_id).state == TaskState.PLANNING

    task_manager.complete_task(task.task_id, "Task successfully accomplished.", [{"tool": "fs_read"}])
    assert task_manager.get_task(task.task_id).state == TaskState.COMPLETED
    assert len(task_manager.get_task(task.task_id).actions) == 1

@pytest.mark.asyncio
async def test_30_react_system_prompt_generation():
    desc = get_tools_prompt_description()
    assert "fs_read" in desc
    assert "fs_write" in desc
    assert "terminal_exec" in desc
    assert "web_search" in desc

# ==================== SECURITY HARDENING REGRESSION TESTS ====================

@pytest.mark.asyncio
async def test_31_fs_sibling_directory_collision():
    with pytest.raises(PermissionError) as exc_info:
        _resolve_safe_path("../workspace_backup/secret.txt")
    assert "escapes workspace sandbox" in str(exc_info.value)

@pytest.mark.asyncio
async def test_32_fs_drive_letter_bypass():
    with pytest.raises((PermissionError, FileNotFoundError)):
        # Drive letter absolute path gets jailed or blocked
        res_path = _resolve_safe_path("C:\\Windows\\System32\\calc.exe", must_exist=True)

@pytest.mark.asyncio
async def test_33_fs_unc_and_device_path_rejection():
    with pytest.raises(PermissionError) as exc_info:
        _resolve_safe_path("\\\\evil-server\\share\\malware.exe")
    assert "UNC and device paths are prohibited" in str(exc_info.value)

@pytest.mark.asyncio
async def test_34_fs_reserved_device_names():
    with pytest.raises(PermissionError) as exc_info:
        _resolve_safe_path("CON.txt")
    assert "Access to reserved device name" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info:
        _resolve_safe_path("sub/NUL")
    assert "Access to reserved device name" in str(exc_info.value)

@pytest.mark.asyncio
async def test_35_fs_null_byte_injection():
    with pytest.raises(PermissionError) as exc_info:
        _resolve_safe_path("innocent.txt\x00.exe")
    assert "Null byte detected" in str(exc_info.value)

@pytest.mark.asyncio
async def test_36_fs_empty_and_whitespace_input():
    with pytest.raises(ValueError) as exc_info:
        _resolve_safe_path("   ")
    assert "empty or whitespace-only" in str(exc_info.value)

@pytest.mark.asyncio
async def test_37_terminal_chaining_rejection():
    res = execute_terminal_command("dir && whoami")
    assert res["status"] == "error"
    assert "prohibited shell metacharacters" in res["message"]

@pytest.mark.asyncio
async def test_38_terminal_subcommand_install_blocking():
    res = execute_terminal_command("pip install malicious-pkg")
    assert res["status"] == "error"
    assert "restricted in sandbox" in res["message"]

@pytest.mark.asyncio
async def test_39_fs_symlink_junction_escape(tmp_path):
    import os
    from pathlib import Path
    from app.config import settings

    workspace_root = Path(settings.WORKSPACE_DIR).resolve()
    outside_target = tmp_path / "outside_secret.txt"
    outside_target.write_text("classified data", encoding="utf-8")
    
    symlink_path = workspace_root / "test_symlink_escape"
    try:
        if symlink_path.exists() or symlink_path.is_symlink():
            if symlink_path.is_dir():
                os.rmdir(symlink_path)
            else:
                os.remove(symlink_path)
        
        # Attempt to create symlink (or test logical resolution if OS restricts privilege)
        try:
            os.symlink(outside_target, symlink_path)
            with pytest.raises(PermissionError) as exc_info:
                _resolve_safe_path("test_symlink_escape", must_exist=True)
            assert "escapes workspace sandbox" in str(exc_info.value)
        except OSError:
            # On Windows without developer mode/admin, symlink creation might raise privilege error
            # Test direct relative path resolution outside root
            with pytest.raises(PermissionError) as exc_info:
                _resolve_safe_path("../../../outside.txt")
            assert "escapes workspace sandbox" in str(exc_info.value)
    finally:
        if symlink_path.exists() or symlink_path.is_symlink():
            try:
                os.remove(symlink_path)
            except Exception:
                pass

@pytest.mark.asyncio
async def test_40_fs_internal_safe_relative_path():
    fs_write("sub/nested.txt", "Nested Content")
    # Legitimate relative path that uses .. internally but remains inside workspace
    resolved = _resolve_safe_path("sub/../sub/nested.txt", must_exist=True)
    assert resolved.endswith("nested.txt")
    read_res = fs_read("sub/../sub/nested.txt")
    assert read_res["status"] == "success"
    assert read_res["content"] == "Nested Content"
    fs_delete("sub/nested.txt")

# ==================== PII ENCRYPTION & DELETION TESTS ====================

import json
import sqlite3
from engine.db import save_interview_session, get_interview_session, delete_interview_session, DB_PATH
from engine.vault import encrypt_data, decrypt_data

@pytest.mark.asyncio
async def test_41_pii_encryption_at_rest():
    test_id = "INT-TEST-ENC-001"
    sample_resume = {
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "phone": "+1-555-0199",
        "skills": ["Python", "FastAPI", "React"]
    }
    sample_jd = {"title": "Senior AI Engineer", "requirements": ["5+ yrs"]}
    
    # Save session
    success = save_interview_session(
        interview_id=test_id,
        resume_data=sample_resume,
        job_description_data=sample_jd,
        domain="AI / ML",
        experience_level="Senior",
        programming_language="Python"
    )
    assert bool(success) is True

    # 1. Inspect raw SQLite row directly — verify ciphertext starts with 'enc::'
    con = sqlite3.connect(DB_PATH)
    cursor = con.cursor()
    cursor.execute("SELECT resume_data, job_description_data FROM interview_sessions WHERE interview_id = ?", (test_id,))
    raw_row = cursor.fetchone()
    con.close()
    
    assert raw_row is not None
    raw_resume_db = raw_row[0]
    assert raw_resume_db.startswith("enc::")
    assert "jane.doe@example.com" not in raw_resume_db  # Raw PII is not in cleartext

    # 2. Retrieve through get_interview_session() — verify automatic transparent decryption
    session = get_interview_session(test_id)
    assert session is not None
    assert session["resume_data"]["name"] == "Jane Doe"
    assert session["resume_data"]["email"] == "jane.doe@example.com"

    # Cleanup
    delete_interview_session(test_id)

@pytest.mark.asyncio
async def test_42_pii_legacy_unencrypted_fallback():
    test_legacy_id = "INT-TEST-LEGACY-002"
    legacy_resume_json = json.dumps({"name": "Legacy User", "email": "legacy@example.com"})
    legacy_jd_json = json.dumps({"title": "Legacy Architect"})

    # Manually insert unencrypted plaintext record (simulating pre-migration database)
    con = sqlite3.connect(DB_PATH)
    cursor = con.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO interview_sessions 
    (interview_id, resume_data, job_description_data, domain, experience_level, programming_language, status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (test_legacy_id, legacy_resume_json, legacy_jd_json, "Backend", "Mid", "Go", "ready"))
    con.commit()
    con.close()

    # Verify get_interview_session() transparently reads legacy plaintext without error
    session = get_interview_session(test_legacy_id)
    assert session is not None
    assert session["resume_data"]["name"] == "Legacy User"
    assert session["resume_data"]["email"] == "legacy@example.com"

    # Cleanup
    delete_interview_session(test_legacy_id)

@pytest.mark.asyncio
async def test_43_candidate_deletion_path():
    test_id = "INT-TEST-DEL-003"
    save_interview_session(
        interview_id=test_id,
        resume_data={"name": "To Delete"},
        job_description_data={"title": "To Delete"},
        domain="QA",
        experience_level="Junior",
        programming_language="TypeScript"
    )
    assert get_interview_session(test_id) is not None

    # Delete session
    del_success = delete_interview_session(test_id)
    assert del_success is True

    # Confirm purged from DB
    assert get_interview_session(test_id) is None

# ==================== SECRETS & ERROR SANITIZATION TESTS ====================

from app.core.sanitizer import sanitize_text

@pytest.mark.asyncio
async def test_44_secrets_sanitization():
    # 1. Test Google Gemini Key sanitization
    raw_gemini_leak = "Error calling https://generativelanguage.googleapis.com/v1beta/models?key=AIzaSyFAKEKEYFAKEKEYFAKEKEYFAKEKEYFA1"
    sanitized_gemini = sanitize_text(raw_gemini_leak)
    assert "AIzaSyFAKEKEYFAKEKEYFAKEKEYFAKEKEYFA1" not in sanitized_gemini
    assert "[REDACTED_GEMINI_KEY]" in sanitized_gemini

    # 2. Test Groq Key sanitization
    raw_groq_leak = "Authorization failure with api_key=gsk_1234567890abcdef1234567890abcdef123456"
    sanitized_groq = sanitize_text(raw_groq_leak)
    assert "gsk_1234567890abcdef1234567890abcdef123456" not in sanitized_groq
    assert "[REDACTED_GROQ_KEY]" in sanitized_groq or "[REDACTED]" in sanitized_groq

    # 3. Test generic URL query param sanitization
    raw_url_leak = "https://api.service.com/endpoint?token=secret_jwt_token_12345&user=admin"
    sanitized_url = sanitize_text(raw_url_leak)
    assert "secret_jwt_token_12345" not in sanitized_url
    assert "token=[REDACTED]" in sanitized_url

# ==================== RELIABILITY & SESSION AUTH TESTS ====================

from app.core.llm_provider import CircuitBreaker
from engine.db import verify_session_token

@pytest.mark.asyncio
async def test_45_interview_scoring_consistency():
    from app.core.interview_engine import RUBRIC
    assert len(RUBRIC) >= 5
    assert 0 in RUBRIC
    assert 10 in RUBRIC

@pytest.mark.asyncio
async def test_46_circuit_breaker_resilience():
    cb = CircuitBreaker("TestProvider", failure_threshold=2, cooldown_seconds=0.5)
    assert cb.can_attempt() is True
    
    cb.record_failure()
    assert cb.can_attempt() is True
    
    cb.record_failure()  # Reaches threshold -> OPEN
    assert cb.state == "OPEN"
    assert cb.can_attempt() is False
    
    # Wait for cooldown
    import asyncio
    await asyncio.sleep(0.6)
    assert cb.can_attempt() is True  # Switches to HALF_OPEN
    assert cb.state == "HALF_OPEN"
    
    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb.consecutive_failures == 0

@pytest.mark.asyncio
async def test_47_session_authorization_tokens():
    test_id = "INT-AUTH-001"
    token = save_interview_session(
        interview_id=test_id,
        resume_data={"name": "Auth Candidate"},
        job_description_data={"title": "Engineer"},
        domain="Backend",
        experience_level="Mid",
        programming_language="Python"
    )
    assert token is not None
    assert token.startswith("tok_")

    # Correct token matches
    assert verify_session_token(test_id, token) is True
    
    # Wrong token fails
    assert verify_session_token(test_id, "tok_fake_wrong_token") is False
    
    # Nonexistent session fails
    assert verify_session_token("NONEXISTENT_SESSION", token) is False

    delete_interview_session(test_id)

@pytest.mark.asyncio
async def test_48_orchestrator_max_attempts_stop():
    from app.core.task_manager import AgentStep
    from app.core.verifier import VerificationResult, verify_step_outcome
    
    step = AgentStep(
        step_number=1,
        goal="Test failure loop limit",
        thought="Attempting impossible step",
        tool_name="fs_read",
        tool_args={"filepath": "non_existent_file.xyz"},
        expected_outcome="File exists and contains magic",
        attempt_count=3,
        max_attempts=3
    )
    
    obs = {"status": "error", "message": "File not found"}
    result: VerificationResult = await verify_step_outcome(step, obs)
    assert result.success is False





