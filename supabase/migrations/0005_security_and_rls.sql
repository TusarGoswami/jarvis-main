-- Migration 0005: Row Level Security (RLS) policies
-- Enables RLS on all user-owned tables and storage buckets, securing access to auth.uid() = user_id.

-- 1. Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tools ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_tools ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.task_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tool_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;

-- 2. Profiles Policies
CREATE POLICY "Users can view their own profile"
    ON public.profiles FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- 3. User Preferences Policies
CREATE POLICY "Users can view their own preferences"
    ON public.user_preferences FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own preferences"
    ON public.user_preferences FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own preferences"
    ON public.user_preferences FOR INSERT WITH CHECK (auth.uid() = user_id);

-- 4. Tools Registry Policies (Global Read, restricted write)
CREATE POLICY "Authenticated users can view tools"
    ON public.tools FOR SELECT USING (auth.role() = 'authenticated');

-- 5. Agents Policies
CREATE POLICY "Users can manage their own agents"
    ON public.agents FOR ALL USING (auth.uid() = user_id);

-- 6. Agent Tools Policies
CREATE POLICY "Users can manage tools of their own agents"
    ON public.agent_tools FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.agents 
            WHERE agents.id = agent_id AND agents.user_id = auth.uid()
        )
    );

-- 7. Conversations Policies
CREATE POLICY "Users can manage their own conversations"
    ON public.conversations FOR ALL USING (auth.uid() = user_id);

-- 8. Messages Policies
CREATE POLICY "Users can manage their own messages"
    ON public.messages FOR ALL USING (auth.uid() = user_id);

-- 9. Agent Memories Policies
CREATE POLICY "Users can manage their own agent memories"
    ON public.agent_memories FOR ALL USING (auth.uid() = user_id);

-- 10. Tasks Policies
CREATE POLICY "Users can manage their own tasks"
    ON public.tasks FOR ALL USING (auth.uid() = user_id);

-- 11. Task Steps Policies
CREATE POLICY "Users can manage steps of their own tasks"
    ON public.task_steps FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.tasks 
            WHERE tasks.id = task_id AND tasks.user_id = auth.uid()
        )
    );

-- 12. Tool Executions Policies
CREATE POLICY "Users can manage tool executions of their own tasks"
    ON public.tool_executions FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.tasks 
            WHERE tasks.id = task_id AND tasks.user_id = auth.uid()
        )
    );

-- 13. Approvals Policies
CREATE POLICY "Users can manage their own approvals"
    ON public.approvals FOR ALL USING (auth.uid() = user_id);

-- 14. Agent Activity Logs Policies
CREATE POLICY "Users can manage their own agent activity logs"
    ON public.agent_activity_logs FOR ALL USING (auth.uid() = user_id);

-- 15. Artifacts Policies
CREATE POLICY "Users can manage their own artifacts"
    ON public.artifacts FOR ALL USING (auth.uid() = user_id);

-- 16. Documents Policies
CREATE POLICY "Users can manage their own documents"
    ON public.documents FOR ALL USING (auth.uid() = user_id);

-- 17. Document Chunks Policies
CREATE POLICY "Users can manage chunks of their own documents"
    ON public.document_chunks FOR ALL USING (auth.uid() = user_id);


-- 18. Supabase Storage Security Policies
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access their own documents"
    ON storage.objects FOR ALL
    USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can access their own artifacts"
    ON storage.objects FOR ALL
    USING (bucket_id = 'artifacts' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Anyone can view avatars"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'avatars');

CREATE POLICY "Users can manage their own avatar"
    ON storage.objects FOR ALL
    USING (bucket_id = 'avatars' AND auth.uid()::text = (storage.foldername(name))[1]);

-- 19. Enable Supabase Realtime for live dashboard updates
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
        BEGIN
            ALTER PUBLICATION supabase_realtime ADD TABLE public.tasks;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END;
        BEGIN
            ALTER PUBLICATION supabase_realtime ADD TABLE public.task_steps;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END;
        BEGIN
            ALTER PUBLICATION supabase_realtime ADD TABLE public.tool_executions;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END;
        BEGIN
            ALTER PUBLICATION supabase_realtime ADD TABLE public.approvals;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END;
        BEGIN
            ALTER PUBLICATION supabase_realtime ADD TABLE public.agent_activity_logs;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END;
        BEGIN
            ALTER PUBLICATION supabase_realtime ADD TABLE public.messages;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END;
    END IF;
END $$;

