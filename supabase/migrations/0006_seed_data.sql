-- Migration 0006: Seed Global Tools Registry
-- Populates the tools registry with core capabilities mapped from the orchestrator manifests.

INSERT INTO public.tools (name, description, category, input_schema, output_schema, permission_level, enabled)
VALUES
    (
        'fs_read',
        'Reads the text content of a file located in the sandboxed workspace.',
        'filesystem',
        '{"type": "object", "properties": {"filepath": {"type": "string", "description": "Relative path of the file to read"}}, "required": ["filepath"]}'::jsonb,
        '{}'::jsonb,
        'low',
        true
    ),
    (
        'fs_write',
        'Creates or overwrites a file with content in the sandboxed workspace.',
        'filesystem',
        '{"type": "object", "properties": {"filepath": {"type": "string", "description": "Relative path of the file to write"}, "content": {"type": "string", "description": "Text content to save"}}, "required": ["filepath", "content"]}'::jsonb,
        '{}'::jsonb,
        'medium',
        true
    ),
    (
        'fs_edit',
        'Replaces an existing text snippet with a new snippet in a workspace file.',
        'filesystem',
        '{"type": "object", "properties": {"filepath": {"type": "string", "description": "Relative path of the file"}, "target_snippet": {"type": "string", "description": "Exact text to replace"}, "replacement_snippet": {"type": "string", "description": "New replacement text"}}, "required": ["filepath", "target_snippet", "replacement_snippet"]}'::jsonb,
        '{}'::jsonb,
        'medium',
        true
    ),
    (
        'fs_list',
        'Lists all files and subdirectories in the workspace.',
        'filesystem',
        '{"type": "object", "properties": {"directory": {"type": "string", "description": "Subdirectory to list, defaults to \'.\'"}}}'::jsonb,
        '{}'::jsonb,
        'low',
        true
    ),
    (
        'fs_delete',
        'Deletes a file or directory from the workspace.',
        'filesystem',
        '{"type": "object", "properties": {"filepath": {"type": "string", "description": "Relative path of the file/folder to delete"}}, "required": ["filepath"]}'::jsonb,
        '{}'::jsonb,
        'high',
        true
    ),
    (
        'terminal_exec',
        'Executes a CLI command or Python program safely inside the workspace sandbox.',
        'terminal',
        '{"type": "object", "properties": {"command": {"type": "string", "description": "CLI command or script to execute (e.g. \'python script.py\')"}}, "required": ["command"]}'::jsonb,
        '{}'::jsonb,
        'medium',
        true
    ),
    (
        'web_search',
        'Searches the live web and extracts summary snippets and citations.',
        'web_search',
        '{"type": "object", "properties": {"query": {"type": "string", "description": "Search query terms"}}, "required": ["query"]}'::jsonb,
        '{}'::jsonb,
        'low',
        true
    ),
    (
        'gui_action',
        'Controls mouse click, typing, hotkey, or scroll at screen coordinates.',
        'system',
        '{"type": "object", "properties": {"action_type": {"type": "string", "enum": ["click", "type", "hotkey", "scroll"]}, "x": {"type": "integer", "description": "Target X screen pixel"}, "y": {"type": "integer", "description": "Target Y screen pixel"}, "text": {"type": "string", "description": "Text to type or scroll amount"}}, "required": ["action_type"]}'::jsonb,
        '{}'::jsonb,
        'medium',
        true
    ),
    (
        'launch_app',
        'Launches an installed desktop application or website via safe PATH.',
        'system',
        '{"type": "object", "properties": {"target": {"type": "string", "description": "Application name or site (e.g. \'notepad\', \'calc\', \'leetcode\')"}}, "required": ["target"]}'::jsonb,
        '{}'::jsonb,
        'low',
        true
    ),
    (
        'system_telemetry',
        'Retrieves live system hardware metrics (CPU, RAM, Disks, Network, Battery).',
        'system',
        '{"type": "object", "properties": {}}'::jsonb,
        '{}'::jsonb,
        'low',
        true
    ),
    (
        'send_email',
        'Sends an email message to a named contact in the database.',
        'communication',
        '{"type": "object", "properties": {"recipient_name": {"type": "string", "description": "The name of the contact"}, "body": {"type": "string", "description": "Body content of the email"}}, "required": ["recipient_name", "body"]}'::jsonb,
        '{}'::jsonb,
        'medium',
        true
    )
ON CONFLICT (name) DO UPDATE 
SET 
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    input_schema = EXCLUDED.input_schema,
    output_schema = EXCLUDED.output_schema,
    permission_level = EXCLUDED.permission_level,
    enabled = EXCLUDED.enabled,
    updated_at = now();
