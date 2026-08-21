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

