from typing import Tuple

DESTRUCTIVE_ACTIONS = {
    "system_shutdown", "system_restart", "delete_file", "format_drive",
    "modify_registry", "kill_process", "send_unconfirmed_payment", "wipe_database"
}

def evaluate_guardrails(intent: str, action_data: dict, confidence: float) -> Tuple[bool, str | None]:
    """
    Evaluates whether an action is safe to execute automatically or requires
    human-in-the-loop explicit confirmation.
    """
    action_type = action_data.get("action", intent)
    
    # Check destructive actions
    if action_type in DESTRUCTIVE_ACTIONS:
        return False, f"Critical action '{action_type}' requires explicit human authorization."

    # Check low confidence threshold
    if confidence < 0.70:
        return False, f"Confidence score ({round(confidence * 100)}%) is below the autonomous execution threshold (70%)."

    return True, None
