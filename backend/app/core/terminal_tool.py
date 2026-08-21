import subprocess
import os
import re
from typing import Dict, Any
from app.config import settings

BLOCKED_COMMANDS = [
    r"\bformat\b",
    r"\brmdir\s+/s",
    r"\bdel\s+/[fFqQsS]*\s+[a-zA-Z]:",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bdiskpart\b",
    r"\breg\s+delete\b",
    r"\brm\s+-rf\s+/",
    r"\bmkfs\b",
    r":\(\)\s*\{"
]

def execute_terminal_command(command: str, timeout_seconds: int = 10) -> Dict[str, Any]:
    """
    Executes a shell or CLI command safely within settings.WORKSPACE_DIR sandbox.
    Prevents execution of destructive system commands.
    """
    os.makedirs(settings.WORKSPACE_DIR, exist_ok=True)
    cmd_clean = command.strip()
    
    if not cmd_clean:
        return {"status": "error", "action": "terminal_exec", "message": "Command cannot be empty."}

    # Guard against blocked dangerous commands
    for pattern in BLOCKED_COMMANDS:
        if re.search(pattern, cmd_clean, re.IGNORECASE):
            return {
                "status": "error",
                "action": "terminal_exec",
                "message": f"Security restriction: Command matched blocked pattern '{pattern}'."
            }

    try:
        proc = subprocess.run(
            cmd_clean,
            shell=True,
            cwd=settings.WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            errors="replace"
        )
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "action": "terminal_exec",
            "command": cmd_clean,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "action": "terminal_exec",
            "command": cmd_clean,
            "message": f"Command timed out after {timeout_seconds} seconds."
        }
    except Exception as e:
        return {
            "status": "error",
            "action": "terminal_exec",
            "command": cmd_clean,
            "message": str(e)
        }
