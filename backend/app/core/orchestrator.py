import re
import json
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable
from google.genai import types

from app.config import settings
from app.core.tools_registry import (
    TOOLS_MANIFEST,
    execute_tool,
    get_tools_prompt_description
)
from app.core.guardrails import evaluate_guardrails
from app.core.llm_provider import generate_multimodal_content

class TaskStep(BaseModel := type("BaseModel", (), {})):
    step_number: int
    thought: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    observation: Optional[Any] = None
    status: str = "pending"  # pending, executing, completed, failed

class OrchestratorResult:
    def __init__(
        self,
        final_text: str,
        steps: List[Dict[str, Any]],
        actions_executed: List[Dict[str, Any]],
        total_latency_ms: float,
        success: bool = True,
        needs_confirmation: bool = False,
        confirmation_reason: Optional[str] = None
    ):
        self.final_text = final_text
        self.steps = steps
        self.actions_executed = actions_executed
        self.total_latency_ms = total_latency_ms
        self.success = success
        self.needs_confirmation = needs_confirmation
        self.confirmation_reason = confirmation_reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_text": self.final_text,
            "steps": self.steps,
            "actions_executed": self.actions_executed,
            "total_latency_ms": self.total_latency_ms,
            "success": self.success,
            "needs_confirmation": self.needs_confirmation,
            "confirmation_reason": self.confirmation_reason
        }

REACT_SYSTEM_PROMPT = """You are Vocalis AI's Autonomous Multi-Tool Agent Orchestrator.
Your goal is to solve the user's task autonomously by planning, using tools, observing results, verifying success, and recovering from errors.

{tools_description}

FORMAT YOUR RESPONSE IN ONE OF TWO MODES:

Mode 1: TOOL EXECUTION NEEDED
If you need to execute a tool, your response MUST follow this exact format:
Thought: <Your step-by-step reasoning on what to do next>
Action: <tool_name>
Action Input: <JSON object matching the tool's parameters>

Example:
Thought: I need to create a test script in the workspace to verify calculations.
Action: fs_write
Action Input: {{"filepath": "test_calc.py", "content": "print(2 + 2)"}}

Mode 2: TASK COMPLETED
When the task is completely finished or no tool is needed:
Thought: <Final verification confirming the task is complete>
Final Answer: <Your comprehensive response to the user>

IMPORTANT RULES:
1. Always inspect the Observation from previous actions to verify whether it succeeded before proceeding.
2. If a command fails or a file isn't found, analyze the error and try an alternative approach.
3. Keep thoughts concise and focused on the objective.
"""

async def run_react_loop(
    user_query: str,
    image_bytes: Optional[bytes] = None,
    client_lang: Optional[str] = None,
    max_turns: int = 5,
    on_step_update: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    allow_actions: bool = True
) -> OrchestratorResult:
    """
    Executes an autonomous ReAct loop: Thought -> Action -> Observation -> Re-plan.
    """
    start_time = time.time()
    steps_log: List[Dict[str, Any]] = []
    actions_executed: List[Dict[str, Any]] = []
    
    if not settings.GEMINI_API_KEY and not settings.GROQ_API_KEY:
        return OrchestratorResult(
            final_text="Vocalis AI is running in offline mode. Please configure GEMINI_API_KEY or GROQ_API_KEY.",
            steps=[],
            actions_executed=[],
            total_latency_ms=round((time.time() - start_time) * 1000, 2),
            success=False
        )

    tools_desc = get_tools_prompt_description()
    system_instruction = REACT_SYSTEM_PROMPT.format(tools_description=tools_desc)

    conversation_history = f"User Request: {user_query}\n"
    
    current_turn = 0
    while current_turn < max_turns:
        current_turn += 1
        
        # Build prompt text
        prompt_text = f"Task Execution Log:\n{conversation_history}\nTurn {current_turn}:"

        try:
            # Shift between Gemini and Groq automatically on rate limit/exhaustion
            raw_output, provider = await generate_multimodal_content(
                prompt_text=prompt_text,
                image_bytes=image_bytes if current_turn == 1 else None,
                system_instruction=system_instruction
            )
        except Exception as e:
            return OrchestratorResult(
                final_text=f"An error occurred while contacting the reasoning model: {str(e)}",
                steps=steps_log,
                actions_executed=actions_executed,
                total_latency_ms=round((time.time() - start_time) * 1000, 2),
                success=False
            )

        # Check if model provided Final Answer
        if "Final Answer:" in raw_output:
            thought = ""
            if "Thought:" in raw_output:
                thought = raw_output.split("Final Answer:")[0].replace("Thought:", "").strip()
            final_ans = raw_output.split("Final Answer:")[1].strip()

            step_record = {
                "step": current_turn,
                "thought": thought or "Task execution complete.",
                "action": None,
                "status": "completed"
            }
            steps_log.append(step_record)
            if on_step_update:
                await on_step_update(step_record)

            return OrchestratorResult(
                final_text=final_ans,
                steps=steps_log,
                actions_executed=actions_executed,
                total_latency_ms=round((time.time() - start_time) * 1000, 2),
                success=True
            )

        # Parse Action & Action Input
        thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|$)", raw_output, re.DOTALL)
        action_match = re.search(r"Action:\s*([a-zA-Z0-9_]+)", raw_output)
        input_match = re.search(r"Action Input:\s*(\{.*?\})", raw_output, re.DOTALL)

        thought = thought_match.group(1).strip() if thought_match else "Reasoning on next step..."
        action_name = action_match.group(1).strip() if action_match else None
        
        action_args = {}
        if input_match:
            try:
                action_args = json.loads(input_match.group(1).strip())
            except Exception:
                # Fallback simple string extraction
                pass

        if not action_name:
            # If no action found, return the output as the final answer
            return OrchestratorResult(
                final_text=raw_output,
                steps=steps_log,
                actions_executed=actions_executed,
                total_latency_ms=round((time.time() - start_time) * 1000, 2),
                success=True
            )

        # Evaluate safety guardrails
        safe, reason = evaluate_guardrails(action_name, action_args, 0.95)
        if not safe:
            step_record = {
                "step": current_turn,
                "thought": thought,
                "action": action_name,
                "args": action_args,
                "status": "waiting_confirmation",
                "confirmation_reason": reason
            }
            steps_log.append(step_record)
            if on_step_update:
                await on_step_update(step_record)

            return OrchestratorResult(
                final_text=f"Action '{action_name}' requires confirmation: {reason}",
                steps=steps_log,
                actions_executed=actions_executed,
                total_latency_ms=round((time.time() - start_time) * 1000, 2),
                success=False,
                needs_confirmation=True,
                confirmation_reason=reason
            )

        # Notify frontend of step execution
        step_record = {
            "step": current_turn,
            "thought": thought,
            "action": action_name,
            "args": action_args,
            "status": "executing"
        }
        steps_log.append(step_record)
        if on_step_update:
            await on_step_update(step_record)

        # Execute Tool
        if allow_actions:
            tool_res = await execute_tool(action_name, action_args)
        else:
            tool_res = {"status": "skipped", "message": "Actions disabled."}

        actions_executed.append(tool_res)
        observation_str = json.dumps(tool_res)
        
        step_record["observation"] = tool_res
        step_record["status"] = "completed" if tool_res.get("status") == "success" else "failed"
        
        if on_step_update:
            await on_step_update(step_record)

        # Append step & observation to history
        conversation_history += f"Thought: {thought}\nAction: {action_name}\nAction Input: {json.dumps(action_args)}\nObservation: {observation_str}\n"

    return OrchestratorResult(
        final_text="Max reasoning turns reached. Multi-step task concluded.",
        steps=steps_log,
        actions_executed=actions_executed,
        total_latency_ms=round((time.time() - start_time) * 1000, 2),
        success=True
    )
