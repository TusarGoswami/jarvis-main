import re
import json
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable

from app.config import settings
from app.core.task_manager import task_manager, TaskState, AgentStep, AgentTask
from app.core.observation import observe_environment, format_observation_for_prompt
from app.core.verifier import verify_step_outcome, VerificationResult
from app.core.tools_registry import execute_tool, get_tools_prompt_description
from app.core.guardrails import evaluate_guardrails
from app.core.llm_provider import generate_multimodal_content

class OrchestratorResult:
    def __init__(
        self,
        final_text: str,
        steps: List[Dict[str, Any]],
        actions_executed: List[Dict[str, Any]],
        total_latency_ms: float,
        success: bool = True,
        needs_confirmation: bool = False,
        confirmation_reason: Optional[str] = None,
        task_id: Optional[str] = None
    ):
        self.final_text = final_text
        self.steps = steps
        self.actions_executed = actions_executed
        self.total_latency_ms = total_latency_ms
        self.success = success
        self.needs_confirmation = needs_confirmation
        self.confirmation_reason = confirmation_reason
        self.task_id = task_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_text": self.final_text,
            "steps": self.steps,
            "actions_executed": self.actions_executed,
            "total_latency_ms": self.total_latency_ms,
            "success": self.success,
            "needs_confirmation": self.needs_confirmation,
            "confirmation_reason": self.confirmation_reason,
            "task_id": self.task_id
        }

PLAN_ACT_OBSERVE_PROMPT = """You are Vocalis AI's Autonomous Multi-Step Agent Orchestrator.
Your goal is to solve user goals autonomously using a Plan -> Act -> Observe -> Verify -> Replan cycle.

{tools_description}

FORMAT YOUR RESPONSE IN ONE OF TWO MODES:

Mode 1: TOOL EXECUTION NEEDED
Thought: <Your step-by-step reasoning on what to do next>
Goal: <Specific sub-goal this single action achieves>
Action: <tool_name>
Action Input: <JSON object matching tool parameters>
Expected Outcome: <Concrete, verifiable state expected after this action executes>

Example:
Thought: I need to write the calculation script into the workspace so it can be executed.
Goal: Create python test script
Action: fs_write
Action Input: {{"filepath": "calc_test.py", "content": "print(10 * 5)"}}
Expected Outcome: File 'calc_test.py' exists on disk with content containing calculation

Mode 2: TASK COMPLETED
Thought: <Final verification confirming the overall goal was achieved>
Final Answer: <Your comprehensive response to the user summarizing the actions taken>

CRITICAL RULES:
1. Always inspect the Observation from the previous step. If a verification failed, analyze the error and try an alternative approach.
2. Formulate a precise Expected Outcome so the environment verifier can check if your action really worked.
3. Keep thoughts focused, direct, and concise.
"""

async def run_react_loop(
    user_query: str,
    image_bytes: Optional[bytes] = None,
    client_lang: Optional[str] = None,
    max_turns: int = 10,
    on_step_update: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    allow_actions: bool = True
) -> OrchestratorResult:
    """
    Executes an autonomous Plan -> Act -> Observe -> Verify -> Replan multi-step agent loop.
    """
    start_time = time.time()
    
    if not settings.GEMINI_API_KEY and not settings.GROQ_API_KEY:
        return OrchestratorResult(
            final_text="Api has been exhausted, plz try after sometime",
            steps=[],
            actions_executed=[],
            total_latency_ms=round((time.time() - start_time) * 1000, 2),
            success=False
        )

    # 1. Initialize AgentTask in TaskManager
    task: AgentTask = task_manager.create_task(query=user_query)
    task_manager.update_state(task.task_id, TaskState.PLANNING)
    
    steps_log: List[Dict[str, Any]] = []
    actions_executed: List[Dict[str, Any]] = []

    tools_desc = get_tools_prompt_description()
    system_instruction = PLAN_ACT_OBSERVE_PROMPT.format(tools_description=tools_desc)

    conversation_history = f"User Request: {user_query}\n"
    
    current_step_num = 1
    attempt_count = 0
    max_step_attempts = 3
    total_turns = 0

    while total_turns < max_turns:
        total_turns += 1
        
        prompt_text = f"Execution History:\n{conversation_history}\nStep {current_step_num} (Attempt {attempt_count + 1}):"

        try:
            raw_output, _ = await generate_multimodal_content(
                prompt_text=prompt_text,
                image_bytes=image_bytes if total_turns == 1 else None,
                system_instruction=system_instruction
            )
        except Exception as e:
            task_manager.fail_task(task.task_id, str(e))
            return OrchestratorResult(
                final_text=f"An error occurred while contacting the reasoning model: {str(e)}",
                steps=steps_log,
                actions_executed=actions_executed,
                total_latency_ms=round((time.time() - start_time) * 1000, 2),
                success=False,
                task_id=task.task_id
            )

        # 2. Check if Task is Completed
        if "Final Answer:" in raw_output:
            thought = ""
            if "Thought:" in raw_output:
                thought = raw_output.split("Final Answer:")[0].replace("Thought:", "").strip()
            final_ans = raw_output.split("Final Answer:")[1].strip()

            step_record = {
                "step": current_step_num,
                "thought": thought or "Task execution complete and verified.",
                "action": None,
                "status": "completed"
            }
            steps_log.append(step_record)
            task_manager.complete_task(task.task_id, final_ans, actions_executed)
            
            if on_step_update:
                await on_step_update(step_record)

            return OrchestratorResult(
                final_text=final_ans,
                steps=steps_log,
                actions_executed=actions_executed,
                total_latency_ms=round((time.time() - start_time) * 1000, 2),
                success=True,
                task_id=task.task_id
            )

        # 3. Parse Thought, Goal, Action, Action Input, Expected Outcome
        thought_match = re.search(r"Thought:\s*(.*?)(?=Goal:|Action:|$)", raw_output, re.DOTALL)
        goal_match = re.search(r"Goal:\s*(.*?)(?=Action:|$)", raw_output, re.DOTALL)
        action_match = re.search(r"Action:\s*([a-zA-Z0-9_]+)", raw_output)
        input_match = re.search(r"Action Input:\s*(\{.*?\})", raw_output, re.DOTALL)
        expected_match = re.search(r"Expected Outcome:\s*(.*?)(?=Thought:|Action:|$)", raw_output, re.DOTALL)

        thought = thought_match.group(1).strip() if thought_match else "Analyzing next step..."
        goal = goal_match.group(1).strip() if goal_match else f"Execute step {current_step_num}"
        action_name = action_match.group(1).strip() if action_match else None
        expected_outcome = expected_match.group(1).strip() if expected_match else None

        action_args = {}
        if input_match:
            try:
                action_args = json.loads(input_match.group(1).strip())
            except Exception:
                pass

        if not action_name:
            # If no action recognized, return response directly
            task_manager.complete_task(task.task_id, raw_output, actions_executed)
            return OrchestratorResult(
                final_text=raw_output,
                steps=steps_log,
                actions_executed=actions_executed,
                total_latency_ms=round((time.time() - start_time) * 1000, 2),
                success=True,
                task_id=task.task_id
            )

        # Create AgentStep object
        step = AgentStep(
            step_number=current_step_num,
            goal=goal,
            thought=thought,
            tool_name=action_name,
            tool_args=action_args,
            expected_outcome=expected_outcome,
            status="executing",
            attempt_count=attempt_count + 1,
            max_attempts=max_step_attempts
        )

        # 4. Evaluate Safety Guardrails
        safe, reason = evaluate_guardrails(
            intent=action_name,
            action_data=action_args,
            confidence=0.95,
            tool_name=action_name,
            tool_args=action_args
        )
        if not safe:
            step.status = "waiting_approval"
            task_manager.add_step(task.task_id, step)
            task_manager.update_state(task.task_id, TaskState.WAITING_APPROVAL, reason=reason)
            
            step_record = {
                "step": current_step_num,
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
                confirmation_reason=reason,
                task_id=task.task_id
            )

        # Notify UI of Step Execution
        step_record = {
            "step": current_step_num,
            "thought": thought,
            "goal": goal,
            "action": action_name,
            "args": action_args,
            "attempt": attempt_count + 1,
            "status": "executing"
        }
        steps_log.append(step_record)
        if on_step_update:
            await on_step_update(step_record)

        # 5. ACT: Execute Tool
        task_manager.update_state(task.task_id, TaskState.EXECUTING)
        if allow_actions:
            tool_res = await execute_tool(action_name, action_args)
        else:
            tool_res = {"status": "skipped", "message": "Actions disabled."}

        actions_executed.append(tool_res)

        # 6. OBSERVE: Environment State Inspection
        task_manager.update_state(task.task_id, TaskState.OBSERVING)
        observation = observe_environment(
            tool_name=action_name,
            tool_args=action_args,
            tool_result=tool_res
        )
        step.observation = observation
        step_record["observation"] = tool_res

        # 7. VERIFY: Compare Expected vs Actual Outcome
        task_manager.update_state(task.task_id, TaskState.VERIFYING)
        verification: VerificationResult = await verify_step_outcome(step, observation)
        step.verification = verification.model_dump()
        step_record["verification"] = verification.model_dump()

        if verification.success:
            # Verification Passed -> Advance to next step
            step.status = "passed"
            step.completed_at = time.time()
            task_manager.add_step(task.task_id, step)
            step_record["status"] = "completed"
            
            if on_step_update:
                await on_step_update(step_record)

            obs_prompt_str = format_observation_for_prompt(observation)
            conversation_history += (
                f"Thought: {thought}\n"
                f"Goal: {goal}\n"
                f"Action: {action_name}\n"
                f"Action Input: {json.dumps(action_args)}\n"
                f"{obs_prompt_str}\n"
                f"Verification: PASSED ({verification.reason})\n"
            )

            current_step_num += 1
            attempt_count = 0  # Reset attempt counter on success

        else:
            # Verification Failed -> REPLAN
            attempt_count += 1
            step.error_message = verification.reason
            step.status = "replanned" if attempt_count < max_step_attempts else "failed"
            task_manager.add_step(task.task_id, step)
            task_manager.update_state(task.task_id, TaskState.REPLANNING)
            
            step_record["status"] = "replanning"
            step_record["error"] = verification.reason
            
            if on_step_update:
                await on_step_update(step_record)

            if attempt_count >= max_step_attempts:
                task_manager.fail_task(task.task_id, f"Step {current_step_num} failed after {max_step_attempts} attempts: {verification.reason}")
                return OrchestratorResult(
                    final_text=f"Task could not be completed after {max_step_attempts} attempts on Step {current_step_num}. Error: {verification.reason}",
                    steps=steps_log,
                    actions_executed=actions_executed,
                    total_latency_ms=round((time.time() - start_time) * 1000, 2),
                    success=False,
                    task_id=task.task_id
                )

            # Feed failure details into next prompt for self-correction
            obs_prompt_str = format_observation_for_prompt(observation)
            conversation_history += (
                f"Thought: {thought}\n"
                f"Goal: {goal}\n"
                f"Action: {action_name}\n"
                f"Action Input: {json.dumps(action_args)}\n"
                f"{obs_prompt_str}\n"
                f"Verification: FAILED ({verification.reason})\n"
                f"Instruction: Your previous action did NOT achieve the goal. Analyze why it failed, change your parameters or select an alternative tool, and replan.\n"
            )

    task_manager.complete_task(task.task_id, "Max reasoning steps completed.", actions_executed)
    return OrchestratorResult(
        final_text="Multi-step task completed across reasoning steps.",
        steps=steps_log,
        actions_executed=actions_executed,
        total_latency_ms=round((time.time() - start_time) * 1000, 2),
        success=True,
        task_id=task.task_id
    )
