import re
from typing import Tuple, Dict, Any, Optional

DESTRUCTIVE_ACTIONS = {
    "system_shutdown", "system_restart", "delete_file", "format_drive",
    "modify_registry", "kill_process", "send_unconfirmed_payment", "wipe_database",
    "fs_delete"
}

DANGEROUS_PATTERNS = [
    r"\brm\s+-(?:r|f|rf|fr)\b",
    r"\bdel\s+/[sfq]\b",
    r"\bformat\s+[a-z]:\b",
    r"\bshutdown\b",
    r"\bdrop\s+(?:table|database|schema)\b",
    r"\bkill\s+-9\b",
    r"\btaskkill\s+/f\b"
]

def evaluate_guardrails(
    intent: str,
    action_data: Optional[Dict[str, Any]] = None,
    confidence: float = 1.0,
    tool_name: Optional[str] = None,
    tool_args: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Evaluates whether an action is safe to execute automatically or requires
    human-in-the-loop explicit confirmation.
    """
    data = action_data or {}
    args = tool_args or {}
    action_type = tool_name or data.get("action", intent)
    
    # 1. Check destructive action names
    if action_type in DESTRUCTIVE_ACTIONS:
        return False, f"Critical action '{action_type}' requires explicit human authorization."

    # 2. Check dangerous terminal command patterns
    if action_type == "terminal_exec":
        cmd = args.get("command", "") or data.get("command", "")
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return False, f"Command contains potentially destructive operation ('{cmd}'). Explicit human approval required."

    # 3. Check low confidence threshold
    if confidence < 0.70:
        return False, f"Confidence score ({round(confidence * 100)}%) is below the autonomous execution threshold (70%)."

    return True, None

