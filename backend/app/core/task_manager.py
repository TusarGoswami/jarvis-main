import uuid
import time
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel

class TaskState(str, Enum):
    RECEIVED = "RECEIVED"
    PLANNING = "PLANNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AgentTask(BaseModel):
    task_id: str
    query: str
    state: TaskState = TaskState.RECEIVED
    steps: List[Dict[str, Any]] = []
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

    def update_state(self, task_id: str, new_state: TaskState, reason: Optional[str] = None):
        if task_id in self._tasks:
            self._tasks[task_id].state = new_state
            self._tasks[task_id].updated_at = time.time()
            if reason:
                self._tasks[task_id].confirmation_reason = reason

    def add_step(self, task_id: str, step_data: Dict[str, Any]):
        if task_id in self._tasks:
            self._tasks[task_id].steps.append(step_data)
            self._tasks[task_id].updated_at = time.time()

    def complete_task(self, task_id: str, final_output: str, actions: List[Dict[str, Any]]):
        if task_id in self._tasks:
            self._tasks[task_id].state = TaskState.COMPLETED
            self._tasks[task_id].final_output = final_output
            self._tasks[task_id].actions = actions
            self._tasks[task_id].updated_at = time.time()

    def fail_task(self, task_id: str, error_message: str):
        if task_id in self._tasks:
            self._tasks[task_id].state = TaskState.FAILED
            self._tasks[task_id].final_output = error_message
            self._tasks[task_id].updated_at = time.time()

    def get_task(self, task_id: str) -> Optional[AgentTask]:
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[AgentTask]:
        return list(self._tasks.values())

task_manager = TaskManager()
