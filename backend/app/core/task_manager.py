import uuid
import time
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

class TaskState(str, Enum):
    RECEIVED = "RECEIVED"
    PLANNING = "PLANNING"
    ANALYZING = "ANALYZING"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    VERIFYING = "VERIFYING"
    REPLANNING = "REPLANNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    WAITING_USER = "WAITING_USER"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class AgentStep(BaseModel):
    step_number: int
    goal: str
    thought: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    expected_outcome: Optional[str] = None
    observation: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, executing, observing, verifying, passed, failed, replanned
    attempt_count: int = 0
    max_attempts: int = 3
    error_message: Optional[str] = None
    started_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None

class AgentTask(BaseModel):
    task_id: str
    query: str
    state: TaskState = TaskState.RECEIVED
    steps: List[AgentStep] = []
    actions: List[Dict[str, Any]] = []
    created_at: float
    updated_at: float
    final_output: Optional[str] = None
    confirmation_reason: Optional[str] = None

class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, AgentTask] = {}

    def create_task(self, query: str) -> AgentTask:
        tid = f"task_{uuid.uuid4().hex[:8]}"
        now = time.time()
        task = AgentTask(
            task_id=tid,
            query=query,
            state=TaskState.RECEIVED,
            steps=[],
            actions=[],
            created_at=now,
            updated_at=now
        )
        self._tasks[tid] = task
        return task

    def update_state(self, task_id: str, new_state: TaskState, reason: Optional[str] = None) -> Optional[AgentTask]:
        if task_id in self._tasks:
            self._tasks[task_id].state = new_state
            self._tasks[task_id].updated_at = time.time()
            if reason:
                self._tasks[task_id].confirmation_reason = reason
            return self._tasks[task_id]
        return None

    def add_step(self, task_id: str, step: AgentStep) -> Optional[AgentStep]:
        if task_id in self._tasks:
            self._tasks[task_id].steps.append(step)
            self._tasks[task_id].updated_at = time.time()
            return step
        return None

    def update_step(self, task_id: str, step_number: int, **kwargs) -> Optional[AgentStep]:
        if task_id in self._tasks:
            task = self._tasks[task_id]
            for s in task.steps:
                if s.step_number == step_number:
                    for k, v in kwargs.items():
                        if hasattr(s, k):
                            setattr(s, k, v)
                    task.updated_at = time.time()
                    return s
        return None

    def get_current_step(self, task_id: str) -> Optional[AgentStep]:
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if task.steps:
                return task.steps[-1]
        return None

    def complete_task(self, task_id: str, final_output: str, actions: List[Dict[str, Any]]) -> Optional[AgentTask]:
        if task_id in self._tasks:
            self._tasks[task_id].state = TaskState.COMPLETED
            self._tasks[task_id].final_output = final_output
            self._tasks[task_id].actions = actions
            self._tasks[task_id].updated_at = time.time()
            return self._tasks[task_id]
        return None

    def fail_task(self, task_id: str, error_message: str) -> Optional[AgentTask]:
        if task_id in self._tasks:
            self._tasks[task_id].state = TaskState.FAILED
            self._tasks[task_id].final_output = error_message
            self._tasks[task_id].updated_at = time.time()
            return self._tasks[task_id]
        return None

    def cancel_task(self, task_id: str, reason: str = "Cancelled by user") -> Optional[AgentTask]:
        if task_id in self._tasks:
            self._tasks[task_id].state = TaskState.CANCELLED
            self._tasks[task_id].final_output = reason
            self._tasks[task_id].updated_at = time.time()
            return self._tasks[task_id]
        return None

    def get_task(self, task_id: str) -> Optional[AgentTask]:
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[AgentTask]:
        return list(self._tasks.values())

task_manager = TaskManager()
