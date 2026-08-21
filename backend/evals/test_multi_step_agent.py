import pytest
import asyncio
import os
from app.core.task_manager import task_manager, TaskState, AgentStep
from app.core.observation import observe_environment, format_observation_for_prompt
from app.core.verifier import verify_step_outcome, VerificationResult
from app.core.guardrails import evaluate_guardrails
from app.config import settings
from app.core.fs_tools import fs_write, fs_read, fs_delete
from app.core.orchestrator import run_react_loop

# ==================== MULTI-STEP AGENT CORE UNIT TESTS ====================

def test_task_manager_lifecycle():
    task = task_manager.create_task("Create a test script and run it")
    assert task.state == TaskState.RECEIVED
    
    # State transitions
    task_manager.update_state(task.task_id, TaskState.PLANNING)
    assert task_manager.get_task(task.task_id).state == TaskState.PLANNING
    
    # Add step
    step = AgentStep(
        step_number=1,
        goal="Write python script",
        thought="Need to generate calculation",
        tool_name="fs_write",
        tool_args={"filepath": "test_agent_script.py", "content": "print(42)"},
        expected_outcome="File exists on disk",
        status="executing"
    )
    task_manager.add_step(task.task_id, step)
    
    current_step = task_manager.get_current_step(task.task_id)
    assert current_step is not None
    assert current_step.step_number == 1
    assert current_step.goal == "Write python script"

    # Complete task
    task_manager.complete_task(task.task_id, "All steps verified successfully.", [{"action": "fs_write"}])
    assert task_manager.get_task(task.task_id).state == TaskState.COMPLETED

def test_observation_engine_filesystem():
    # 1. Write a file
    test_file = "obs_test_file.txt"
    fs_write(test_file, "Hello Vocalis Observation Engine!")
    
    obs = observe_environment("fs_write", {"filepath": test_file}, {"status": "success"})
    assert obs["environment_state"]["file_exists"] is True
    assert obs["environment_state"]["size_bytes"] > 0
    assert "Hello Vocalis" in obs["environment_state"]["content_sample"]
    
    prompt_str = format_observation_for_prompt(obs)
    assert "Exists on Disk: True" in prompt_str
    
    # Cleanup
    fs_delete(test_file)
    obs_del = observe_environment("fs_delete", {"filepath": test_file}, {"status": "success"})
    assert obs_del["environment_state"]["file_exists"] is False
    assert obs_del["environment_state"]["deletion_verified"] is True

def test_guardrails_dangerous_commands():
    # Safe terminal command
    safe, _ = evaluate_guardrails("terminal_exec", {"command": "python --version"}, 0.95, "terminal_exec", {"command": "python --version"})
    assert safe is True
    
    # Dangerous rm -rf
    safe_rm, reason_rm = evaluate_guardrails("terminal_exec", {"command": "rm -rf /"}, 0.95, "terminal_exec", {"command": "rm -rf /"})
    assert safe_rm is False
    assert "potentially destructive" in reason_rm
    
    # Dangerous shutdown
    safe_sd, reason_sd = evaluate_guardrails("terminal_exec", {"command": "shutdown /s /t 0"}, 0.95, "terminal_exec", {"command": "shutdown /s /t 0"})
    assert safe_sd is False
    
    # Destructive fs_delete
    safe_del, reason_del = evaluate_guardrails("fs_delete", {"filepath": "important.db"}, 0.95, "fs_delete", {"filepath": "important.db"})
    assert safe_del is False
    assert "requires explicit human authorization" in reason_del

@pytest.mark.asyncio
async def test_verifier_deterministic_pass_and_fail():
    # Test pass
    step_pass = AgentStep(
        step_number=1,
        goal="Create note",
        thought="Writing note",
        tool_name="fs_write",
        tool_args={"filepath": "test_pass.txt", "content": "Sample content"},
        expected_outcome="File exists with content"
    )
    obs_pass = {
        "tool_name": "fs_write",
        "tool_status": "success",
        "raw_result": {"status": "success"},
        "environment_state": {"file_exists": True, "size_bytes": 14, "filepath": "test_pass.txt"}
    }
    res_pass = await verify_step_outcome(step_pass, obs_pass)
    assert res_pass.success is True

    # Test failure: tool returned error
    obs_fail = {
        "tool_name": "fs_write",
        "tool_status": "error",
        "raw_result": {"status": "error", "message": "Permission denied"},
        "environment_state": {}
    }
    res_fail = await verify_step_outcome(step_pass, obs_fail)
    assert res_fail.success is False
    assert res_fail.retryable is True
    assert "Permission denied" in res_fail.reason

    # Test failure: file missing on disk
    obs_missing = {
        "tool_name": "fs_write",
        "tool_status": "success",
        "raw_result": {"status": "success"},
        "environment_state": {"file_exists": False, "filepath": "test_pass.txt"}
    }
    res_missing = await verify_step_outcome(step_pass, obs_missing)
    assert res_missing.success is False
    assert "was not found on disk" in res_missing.reason
