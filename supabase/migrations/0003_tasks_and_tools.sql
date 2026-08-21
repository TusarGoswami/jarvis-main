-- Migration 0003: Tasks, Task Steps, Tool Executions, Approvals, logs, and Artifacts
-- Creates the orchestration, security human-in-the-loop approvals, and audit trail tables.

-- 1. Tasks Table (with parent-child subtasks relationship)
CREATE TABLE IF NOT EXISTS public.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE CASCADE,
    parent_task_id UUID REFERENCES public.tasks(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'planning', 'waiting_approval', 'executing', 'observing', 'verifying', 'replanning', 'completed', 'failed', 'cancelled')) NOT NULL,
    priority INTEGER DEFAULT 0 NOT NULL,
    input JSONB DEFAULT '{}'::jsonb NOT NULL,
    output JSONB DEFAULT '{}'::jsonb NOT NULL,
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON public.tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_agent_id ON public.tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON public.tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON public.tasks(status);

-- 2. Task Steps Table
CREATE TABLE IF NOT EXISTS public.task_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'executing', 'completed', 'failed', 'cancelled')) NOT NULL,
    tool_id UUID REFERENCES public.tools(id) ON DELETE SET NULL,
    input JSONB DEFAULT '{}'::jsonb NOT NULL,
    output JSONB DEFAULT '{}'::jsonb NOT NULL,
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE (task_id, step_number)
);

CREATE INDEX IF NOT EXISTS idx_task_steps_task_id ON public.task_steps(task_id);

-- 3. Tool Executions Table (Observability and performance statistics)
CREATE TABLE IF NOT EXISTS public.tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES public.tasks(id) ON DELETE CASCADE,
    task_step_id UUID REFERENCES public.task_steps(id) ON DELETE CASCADE,
    tool_id UUID NOT NULL REFERENCES public.tools(id) ON DELETE RESTRICT,
    agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
    status TEXT CHECK (status IN ('queued', 'executing', 'completed', 'failed')) NOT NULL,
    input JSONB DEFAULT '{}'::jsonb NOT NULL,
    output JSONB DEFAULT '{}'::jsonb NOT NULL,
    error TEXT,
    execution_time_ms INTEGER,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tool_executions_task_id ON public.tool_executions(task_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_step_id ON public.tool_executions(task_step_id);

-- 4. Approvals Table (Human-in-the-loop security authorization)
CREATE TABLE IF NOT EXISTS public.approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    task_id UUID REFERENCES public.tasks(id) ON DELETE CASCADE,
    tool_execution_id UUID REFERENCES public.tool_executions(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    risk_level TEXT DEFAULT 'low' CHECK (risk_level IN ('low', 'medium', 'high', 'critical')) NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired')) NOT NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_approvals_user_id ON public.approvals(user_id);
CREATE INDEX IF NOT EXISTS idx_approvals_task_id ON public.approvals(task_id);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON public.approvals(status);

-- 5. Agent Activity Logs Table (Real-time events stream)
CREATE TABLE IF NOT EXISTS public.agent_activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES public.agents(id) ON DELETE CASCADE,
    task_id UUID REFERENCES public.tasks(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON public.agent_activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_agent_id ON public.agent_activity_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_task_id ON public.agent_activity_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON public.agent_activity_logs(created_at);

-- 6. Files / Artifacts Table (Generated or uploaded assets)
CREATE TABLE IF NOT EXISTS public.artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    task_id UUID REFERENCES public.tasks(id) ON DELETE SET NULL,
    agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type TEXT,
    size BIGINT,
    artifact_type TEXT NOT NULL CHECK (artifact_type IN ('file', 'code', 'data', 'report', 'image', 'document', 'output')),
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_artifacts_user_id ON public.artifacts(user_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_task_id ON public.artifacts(task_id);
