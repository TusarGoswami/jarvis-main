import json
from typing import Dict, Any, Callable, List, Optional
from pydantic import BaseModel

from app.core.fs_tools import fs_read, fs_write, fs_edit, fs_list, fs_delete
from app.core.terminal_tool import execute_terminal_command
from app.core.web_tool import search_and_scrape
from app.core.tools import execute_gui_action, launch_target, get_system_stats
from app.core.email_tool import send_email

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    risk_level: str  # 'low', 'medium', 'high'
    requires_approval: bool = False

# Tool Manifests
TOOLS_MANIFEST: Dict[str, ToolDefinition] = {
    "fs_read": ToolDefinition(
        name="fs_read",
        description="Reads the text content of a file located in the sandboxed workspace.",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Relative path of the file to read"}
            },
            "required": ["filepath"]
        },
        risk_level="low"
    ),
    "fs_write": ToolDefinition(
        name="fs_write",
        description="Creates or overwrites a file with content in the sandboxed workspace.",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Relative path of the file to write"},
                "content": {"type": "string", "description": "Text content to save"}
            },
            "required": ["filepath", "content"]
        },
        risk_level="medium"
    ),
    "fs_edit": ToolDefinition(
        name="fs_edit",
        description="Replaces an existing text snippet with a new snippet in a workspace file.",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Relative path of the file"},
                "target_snippet": {"type": "string", "description": "Exact text to replace"},
                "replacement_snippet": {"type": "string", "description": "New replacement text"}
            },
            "required": ["filepath", "target_snippet", "replacement_snippet"]
        },
        risk_level="medium"
    ),
    "fs_list": ToolDefinition(
        name="fs_list",
        description="Lists all files and subdirectories in the workspace.",
        parameters={
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Subdirectory to list, defaults to '.'"}
            }
        },
        risk_level="low"
    ),
    "fs_delete": ToolDefinition(
        name="fs_delete",
        description="Deletes a file or directory from the workspace.",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Relative path of the file/folder to delete"}
            },
            "required": ["filepath"]
        },
        risk_level="high",
        requires_approval=True
    ),
    "terminal_exec": ToolDefinition(
        name="terminal_exec",
        description="Executes a CLI command or Python program safely inside the workspace sandbox.",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "CLI command or script to execute (e.g. 'python script.py')"}
            },
            "required": ["command"]
        },
        risk_level="medium"
    ),
    "web_search": ToolDefinition(
        name="web_search",
        description="Searches the live web and extracts summary snippets and citations.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query terms"}
            },
            "required": ["query"]
        },
        risk_level="low"
    ),
    "gui_action": ToolDefinition(
        name="gui_action",
        description="Controls mouse click, typing, hotkey, or scroll at screen coordinates.",
        parameters={
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "enum": ["click", "type", "hotkey", "scroll"]},
                "x": {"type": "integer", "description": "Target X screen pixel"},
                "y": {"type": "integer", "description": "Target Y screen pixel"},
                "text": {"type": "string", "description": "Text to type or scroll amount"}
            },
            "required": ["action_type"]
        },
        risk_level="medium"
    ),
    "launch_app": ToolDefinition(
        name="launch_app",
        description="Launches an installed desktop application or website via safe PATH.",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Application name or site (e.g. 'notepad', 'calc', 'leetcode')"}
            },
            "required": ["target"]
        },
        risk_level="low"
    ),
    "system_telemetry": ToolDefinition(
        name="system_telemetry",
        description="Retrieves live system hardware metrics (CPU, RAM, Disks, Network, Battery).",
        parameters={"type": "object", "properties": {}},
        risk_level="low"
    ),
    "send_email": ToolDefinition(
        name="send_email",
        description="Sends an email via Gmail API to a specified recipient address with subject and body.",
        parameters={
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "The recipient email address (e.g. 'user@example.com')"},
                "subject": {"type": "string", "description": "Subject line of the email"},
                "body": {"type": "string", "description": "Body content of the email"}
            },
            "required": ["to", "body"]
        },
        risk_level="high",
        requires_approval=True
    ),
    "screenshot": ToolDefinition(
        name="screenshot",
        description="Captures the current desktop screen state and visual UI for analysis.",
        parameters={"type": "object", "properties": {}},
        risk_level="low"
    ),
    "observe_screen": ToolDefinition(
        name="observe_screen",
        description="Inspects the visual screen to verify UI state or active application windows.",
        parameters={"type": "object", "properties": {}},
        risk_level="low"
    )
}

async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the specified tool dynamically by name with passed arguments.
    """
    if tool_name not in TOOLS_MANIFEST:
        return {"status": "error", "message": f"Unknown tool: '{tool_name}'"}

    try:
        if tool_name == "fs_read":
            return fs_read(filepath=arguments.get("filepath", ""))
        elif tool_name == "fs_write":
            return fs_write(filepath=arguments.get("filepath", ""), content=arguments.get("content", ""))
        elif tool_name == "fs_edit":
            return fs_edit(
                filepath=arguments.get("filepath", ""),
                target_snippet=arguments.get("target_snippet", ""),
                replacement_snippet=arguments.get("replacement_snippet", "")
            )
        elif tool_name == "fs_list":
            return fs_list(directory=arguments.get("directory", "."))
        elif tool_name == "fs_delete":
            return fs_delete(filepath=arguments.get("filepath", ""))
        elif tool_name == "terminal_exec":
            return execute_terminal_command(command=arguments.get("command", ""))
        elif tool_name == "web_search":
            return await search_and_scrape(query=arguments.get("query", ""))
        elif tool_name == "gui_action":
            return execute_gui_action(
                action_type=arguments.get("action_type", "click"),
                x=arguments.get("x"),
                y=arguments.get("y"),
                text=arguments.get("text")
            )
        elif tool_name == "launch_app":
            return launch_target(target=arguments.get("target", ""))
        elif tool_name == "system_telemetry":
            stats = get_system_stats()
            return {"status": "success", "action": "system_telemetry", "data": stats}
        elif tool_name == "send_email":
            to_addr = arguments.get("to") or arguments.get("recipient_email") or arguments.get("recipient_name") or ""
            subj = arguments.get("subject")
            body_text = arguments.get("body", "")
            return send_email(to=to_addr, subject=subj, body=body_text)
        elif tool_name in ["screenshot", "observe_screen"]:
            from app.core.multimodal import capture_screen_bytes
            s_bytes = capture_screen_bytes()
            return {
                "status": "success",
                "action": tool_name,
                "screen_captured": True,
                "size_bytes": len(s_bytes) if s_bytes else 0
            }

        return {"status": "error", "message": f"Tool '{tool_name}' has no execution handler."}
    except Exception as e:
        return {"status": "error", "tool": tool_name, "message": str(e)}

def get_tools_prompt_description() -> str:
    """
    Generates a clear schema description of all available tools for the LLM system prompt.
    """
    lines = ["Available Tools you can invoke during your multi-step reasoning:"]
    for name, tool in TOOLS_MANIFEST.items():
        params_str = ", ".join(tool.parameters.get("properties", {}).keys())
        lines.append(f"- {name}({params_str}): {tool.description}")
    return "\n".join(lines)
