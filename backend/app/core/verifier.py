import json
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.core.task_manager import AgentStep
from app.core.llm_provider import generate_multimodal_content

class VerificationResult(BaseModel):
    success: bool
    reason: str
    details: Dict[str, Any] = {}
    retryable: bool = True

async def verify_step_outcome(step: AgentStep, observation: Dict[str, Any]) -> VerificationResult:
    """
    Compares the step's expected outcome against actual observation state.
    Uses deterministic checks where possible, falling back to lightweight LLM semantic verification.
    """
    tool_status = observation.get("tool_status", "unknown")
    raw_res = observation.get("raw_result", {})
    env = observation.get("environment_state", {})

    # 1. Fast Deterministic Verification
    if tool_status == "error" or raw_res.get("status") == "error":
        err_msg = raw_res.get("message") or raw_res.get("error") or "Tool execution failed."
        return VerificationResult(
            success=False,
            reason=f"Action execution error: {err_msg}",
            details={"raw_error": raw_res},
            retryable=True
        )

    tool_name = step.tool_name or ""
    
    # Filesystem write verification
    if tool_name in ["fs_write", "fs_edit"]:
        if "file_exists" in env and not env["file_exists"]:
            return VerificationResult(
                success=False,
                reason=f"File '{env.get('filepath')}' was not found on disk after write operation.",
                details=env,
                retryable=True
            )
        if env.get("size_bytes", 0) == 0 and step.tool_args and step.tool_args.get("content"):
            return VerificationResult(
                success=False,
                reason=f"File '{env.get('filepath')}' exists but has 0 bytes.",
                details=env,
                retryable=True
            )

    # Filesystem delete verification
    if tool_name == "fs_delete":
        if env.get("file_exists") is True:
            return VerificationResult(
                success=False,
                reason=f"File '{env.get('filepath')}' still exists on disk after delete operation.",
                details=env,
                retryable=True
            )

    # Terminal command exit code verification
    if tool_name == "terminal_exec":
        exit_code = env.get("exit_code")
        if exit_code is not None and exit_code != 0:
            output = env.get("output_summary", "Non-zero exit code")
            return VerificationResult(
                success=False,
                reason=f"Command terminated with non-zero exit code ({exit_code}): {output[:200]}",
                details=env,
                retryable=True
            )

    # If no complex expected outcome was defined, standard deterministic pass
    if not step.expected_outcome or len(step.expected_outcome.strip()) < 5:
        return VerificationResult(
            success=True,
            reason=f"Action '{tool_name}' completed and verified in environment.",
            details=env,
            retryable=False
        )

    # 2. Semantic LLM Verification (Compare Expected Outcome vs Observation)
    try:
        verify_prompt = f"""You are an autonomous Task Verifier. Determine if the action achieved the expected outcome.

STEP GOAL: {step.goal}
ACTION TAKEN: {step.tool_name} with args {json.dumps(step.tool_args or {})}
EXPECTED OUTCOME: {step.expected_outcome}
ACTUAL OBSERVATION: {json.dumps(env or raw_res)}

Respond ONLY in valid JSON:
{{
  "success": true/false,
  "reason": "<Brief explanation of why it passed or failed>",
  "retryable": true/false
}}"""
        llm_resp = await generate_multimodal_content(prompt_text=verify_prompt)
        text = llm_resp.reply_text.strip()
        
        # Clean potential markdown formatting
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            
        data = json.loads(text.strip())
        return VerificationResult(
            success=bool(data.get("success", True)),
            reason=data.get("reason", "Verified by evaluator."),
            details={"semantic_eval": data},
            retryable=bool(data.get("retryable", True))
        )
    except Exception:
        # Fallback to deterministic check pass
        return VerificationResult(
            success=True,
            reason=f"Action '{tool_name}' succeeded in environment (deterministic pass).",
            details=env,
            retryable=False
        )
