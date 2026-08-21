-- Migration 0004: RAG Documents, Chunks, storage buckets, and Vector Search Functions
-- Creates the document ingestion schema, vector chunks table, registers buckets, and defines RLS-compliant retrieval procedures.

-- 1. Documents Table
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    description TEXT,
    file_path TEXT NOT NULL,
    file_type TEXT,
    file_size BIGINT,
    status TEXT DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'processing', 'processed', 'failed', 'deleted')) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_user_id ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.documents(status);

-- 2. Document Chunks Table
CREATE TABLE IF NOT EXISTS public.document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON public.document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_user_id ON public.document_chunks(user_id);

-- Create HNSW vector index for document chunk retrieval
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON public.document_chunks
USING hnsw (embedding vector_cosine_ops);

-- 3. Register Supabase Storage Buckets
-- Note: inserting directly into storage.buckets is supported by Supabase migrations
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
    ('documents', 'documents', false, null, null),
    ('artifacts', 'artifacts', false, null, null),
    ('avatars', 'avatars', true, null, null)
ON CONFLICT (id) DO NOTHING;

-- 4. PostgreSQL Function: Semantic Memory search_agent_memories
CREATE OR REPLACE FUNCTION public.search_agent_memories(
    p_agent_id UUID,
    p_query_embedding vector(768),
    p_match_threshold REAL,
    p_match_count INTEGER
)
RETURNS TABLE (
    id UUID,
    memory_type TEXT,
    content TEXT,
    metadata JSONB,
    importance REAL,
    similarity REAL,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id, 
        m.memory_type, 
        m.content, 
        m.metadata, 
        m.importance,
        (1 - (m.embedding <=> p_query_embedding))::REAL AS similarity,
        m.created_at
    FROM public.agent_memories m
    -- RLS is automatically applied unless defined as SECURITY DEFINER bypassing RLS.
    -- To ensure security, this function runs with user context.
    WHERE m.agent_id = p_agent_id
      AND (1 - (m.embedding <=> p_query_embedding)) > p_match_threshold
    ORDER BY m.embedding <=> p_query_embedding
    LIMIT p_match_count;
END;
$$ LANGUAGE plpgsql SECURITY INVOKER;

-- 5. PostgreSQL Function: RAG Search search_document_chunks
CREATE OR REPLACE FUNCTION public.search_document_chunks(
    p_user_id UUID,
    p_query_embedding vector(768),
    p_match_threshold REAL,
    p_match_count INTEGER
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    chunk_index INTEGER,
    content TEXT,
    metadata JSONB,
    similarity REAL,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id, 
        c.document_id, 
        c.chunk_index, 
        c.content, 
        c.metadata,
        (1 - (c.embedding <=> p_query_embedding))::REAL AS similarity,
        c.created_at
    FROM public.document_chunks c
    WHERE c.user_id = p_user_id
      AND (1 - (c.embedding <=> p_query_embedding)) > p_match_threshold
    ORDER BY c.embedding <=> p_query_embedding
    LIMIT p_match_count;
END;
$$ LANGUAGE plpgsql SECURITY INVOKER;
