import os
import time
from typing import Dict, Any, Optional
from app.config import settings
from app.core.fs_tools import _resolve_safe_path
from app.core.multimodal import capture_screen_bytes

def observe_environment(
    tool_name: str,
    tool_args: Dict[str, Any],
    tool_result: Dict[str, Any],
    capture_screen: bool = False
) -> Dict[str, Any]:
    """
    Inspects the actual environment state (disk, terminal, or screen)
    after a tool action has executed.
    """
    observation: Dict[str, Any] = {
        "timestamp": time.time(),
        "tool_name": tool_name,
        "tool_status": tool_result.get("status", "unknown"),
        "raw_result": tool_result,
        "environment_state": {}
    }

    # 1. Filesystem Observation
    if tool_name.startswith("fs_") or "filepath" in tool_args:
        filepath = tool_args.get("filepath", "")
        if filepath:
            try:
                full_path = _resolve_safe_path(filepath)
            except Exception:
                full_path = os.path.abspath(os.path.join(settings.WORKSPACE_DIR, filepath))
            exists = os.path.exists(full_path)
            observation["environment_state"]["file_exists"] = exists
            observation["environment_state"]["filepath"] = filepath
            
            if exists:
                try:
                    stat = os.stat(full_path)
                    observation["environment_state"]["size_bytes"] = stat.st_size
                    observation["environment_state"]["modified_at"] = stat.st_mtime
                    # Read sample snippet if it's a file
                    if os.path.isfile(full_path):
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            sample = f.read(500)
                            observation["environment_state"]["content_sample"] = sample
                except Exception as e:
                    observation["environment_state"]["read_error"] = str(e)
            else:
                if tool_name == "fs_delete":
                    observation["environment_state"]["deletion_verified"] = True

    # 2. Terminal Observation
    elif tool_name == "terminal_exec":
        observation["environment_state"]["exit_code"] = tool_result.get("exit_code")
        observation["environment_state"]["has_stdout"] = bool(tool_result.get("stdout"))
        observation["environment_state"]["has_stderr"] = bool(tool_result.get("stderr"))
        observation["environment_state"]["output_summary"] = (
            tool_result.get("stdout") or tool_result.get("stderr") or ""
        )[:500]

    # 3. Web Observation
    elif tool_name in ["web_search", "web_scrape"]:
        observation["environment_state"]["results_count"] = len(tool_result.get("results", []))
        observation["environment_state"]["status"] = tool_result.get("status")

    # 4. Screen Observation
    if capture_screen or tool_name in ["screenshot", "observe_screen", "execute_gui_action"]:
        try:
            screen_bytes = capture_screen_bytes()
            if screen_bytes:
                observation["environment_state"]["screen_captured"] = True
                observation["environment_state"]["screen_bytes_size"] = len(screen_bytes)
        except Exception as e:
            observation["environment_state"]["screen_capture_error"] = str(e)

    return observation

def format_observation_for_prompt(observation: Dict[str, Any]) -> str:
    """
    Formats the structured observation for LLM reasoning and verification.
    """
    tool_name = observation.get("tool_name", "unknown")
    status = observation.get("tool_status", "unknown")
    env = observation.get("environment_state", {})
    raw = observation.get("raw_result", {})

    lines = [f"Observation from {tool_name} (Execution Status: {status}):"]
    
    if "file_exists" in env:
        lines.append(f"- File '{env.get('filepath')}' Exists on Disk: {env.get('file_exists')}")
        if env.get("file_exists"):
            lines.append(f"- File Size: {env.get('size_bytes')} bytes")
            if "content_sample" in env:
                lines.append(f"- Content Snippet: {repr(env.get('content_sample')[:150])}")
        elif env.get("deletion_verified"):
            lines.append("- Deletion Verified: File is confirmed removed from workspace.")

    if "exit_code" in env:
        lines.append(f"- Terminal Process Exit Code: {env.get('exit_code')}")
        if env.get("output_summary"):
            lines.append(f"- Process Output: {env.get('output_summary')}")

    if "screen_captured" in env:
        lines.append(f"- Screen Captured: Yes ({env.get('screen_bytes_size')} bytes)")

    if not env:
        msg = raw.get("message") or raw.get("error") or str(raw)
        lines.append(f"- Tool Result: {msg}")

    return "\n".join(lines)
