import os
import sys
import time
import requests

# Supabase URL and Anon/Publishable Key from the request
SUPABASE_URL = "https://nwabikfqyanjydplpqab.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_7j1oyFJOqXsDphimskf-fw_8Mnzg3wP"

# Mock users for testing
USER_A_EMAIL = "usera_test@vocalis.ai"
PASSWORD = "PasswordTestSecure123!"

# A fake user UUID to verify RLS blocks access
FAKE_USER_ID = "00000000-0000-0000-0000-000000000009"

def get_headers(token=None):
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def authenticate_user(email, password, retries=3):
    """Sign up or sign in a test user to get their JWT token."""
    # Attempt Sign In
    signin_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    r = requests.post(signin_url, json={"email": email, "password": password}, headers=get_headers())
    
    if r.status_code == 200:
        data = r.json()
        return data["access_token"], data["user"]["id"]
    
    # If sign in fails, try signing up
    signup_url = f"{SUPABASE_URL}/auth/v1/signup"
    r = requests.post(signup_url, json={"email": email, "password": password}, headers=get_headers())
    if r.status_code == 200:
        data = r.json()
        if "access_token" in data:
            return data["access_token"], data["user"]["id"]
        else:
            print(f"Signed up {email}, attempting sign in...")
            time.sleep(1.5)
            return authenticate_user(email, password, retries)
            
    # Handle rate limit gracefully
    if r.status_code == 429:
        if retries > 0:
            print(f"  Hit signup rate limit. Retries left: {retries}. Waiting 15 seconds...")
            time.sleep(15)
            return authenticate_user(email, password, retries - 1)
        else:
            raise Exception(
                "Supabase email rate limit exceeded.\n\n"
                "To fix this issue:\n"
                "1. Open your Supabase Dashboard: Settings -> Authentication -> Providers -> Email.\n"
                "2. Turn OFF 'Confirm email' to allow instant, automated testing signups.\n"
                f"3. Or, manually create a user with email '{email}' and password '{password}' in the Auth table."
            )
            
    raise Exception(f"Failed to authenticate user {email}: {r.status_code} - {r.text}")


def run_tests():
    print("=" * 60)
    print("          VOCALIS AI DATABASE TEST SUITE")
    print("=" * 60)

    try:
        # Authenticate User A
        print("\n[1/8] Authenticating test user...")
        token_a, uid_a = authenticate_user(USER_A_EMAIL, PASSWORD)
        print(f"  Authenticated User A: {USER_A_EMAIL} (ID: {uid_a})")
    except Exception as e:
        print(f"Authentication Failed: {e}")
        print("Please verify that the Supabase migrations are applied, and the Auth system is enabled.")
        return

    # Check Profiles and Preferences
    print("\n[2/8] Testing Profiles and User Preferences...")
    headers_a = get_headers(token_a)
    
    # Profiles should exist (auto-created via database trigger)
    r = requests.get(f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{uid_a}", headers=headers_a)
    if r.status_code == 200 and len(r.json()) > 0:
        print("  ✓ Profile A auto-creation verified.")
    else:
        print(f"  ✗ Profile A validation failed. Code: {r.status_code}, Body: {r.text}")

    # Preferences should exist (auto-created via database trigger)
    r = requests.get(f"{SUPABASE_URL}/rest/v1/user_preferences?user_id=eq.{uid_a}", headers=headers_a)
    if r.status_code == 200 and len(r.json()) > 0:
        print("  ✓ User Preferences A auto-creation verified.")
    else:
        print(f"  ✗ Preferences A validation failed. Code: {r.status_code}, Body: {r.text}")

    # Create Agent for User A
    print("\n[3/8] Testing Agent creation...")
    agent_data = {
        "user_id": uid_a,
        "name": "Test Orchestrator",
        "description": "Agent for automated testing",
        "system_prompt": "You are a test agent.",
        "model": "gemini-2.5-flash",
        "provider": "google",
        "status": "active"
    }
    r = requests.post(f"{SUPABASE_URL}/rest/v1/agents", json=agent_data, headers=headers_a)
    if r.status_code == 201 or r.status_code == 200:
        print("  ✓ Created agent for User A.")
    else:
        print(f"  ✗ Failed to create agent. Code: {r.status_code}, Body: {r.text}")
        return
        
    # Get User A's Agent ID
    r = requests.get(f"{SUPABASE_URL}/rest/v1/agents?user_id=eq.{uid_a}", headers=headers_a)
    agent_id = r.json()[0]["id"]

    # Associate tool capability
    # Find tool ID for fs_read
    r = requests.get(f"{SUPABASE_URL}/rest/v1/tools?name=eq.fs_read", headers=headers_a)
    if r.status_code == 200 and len(r.json()) > 0:
        tool_id = r.json()[0]["id"]
        agent_tool_data = {
            "agent_id": agent_id,
            "tool_id": tool_id,
            "enabled": True
        }
        # Postgrest syntax: insert returns 201 on success
        r = requests.post(f"{SUPABASE_URL}/rest/v1/agent_tools", json=agent_tool_data, headers=headers_a)
        if r.status_code == 201 or r.status_code == 409: # 409 is conflict if already associated
            print("  ✓ Associated fs_read tool with agent.")
        else:
            print(f"  ✗ Failed to associate tool. Code: {r.status_code}, Body: {r.text}")
    else:
        print("  ✗ Tools registry not seeded yet.")
        tool_id = None

    # User Isolation RLS test (Single-User isolation check)
    print("\n[4/8] Testing User Isolation (RLS)...")
    
    # 1. User A tries to insert an agent belonging to FAKE_USER_ID
    leaked_agent = {
        "user_id": FAKE_USER_ID,
        "name": "Leaked Agent",
        "model": "gemini-2.5-flash",
        "provider": "google"
    }
    r = requests.post(f"{SUPABASE_URL}/rest/v1/agents", json=leaked_agent, headers=headers_a)
    # This should fail or not be visible due to auth.uid() Check constraint policy
    if r.status_code in (400, 401, 403, 409) or (r.status_code == 201 and r.json() is None):
        print("  ✓ User Isolation Active: Cannot insert agent for another user.")
    else:
        # Let's double check if it was actually inserted
        r_check = requests.get(f"{SUPABASE_URL}/rest/v1/agents?user_id=eq.{FAKE_USER_ID}", headers=headers_a)
        if len(r_check.json()) == 0:
            print("  ✓ User Isolation Active: Cannot insert/view another user's agent.")
        else:
            print(f"  ✗ User Isolation Leaked! Created agent for fake user: {r_check.json()}")

    # 2. Querying other users data should return empty lists
    r = requests.get(f"{SUPABASE_URL}/rest/v1/agents?user_id=eq.{FAKE_USER_ID}", headers=headers_a)
    if r.status_code == 200 and len(r.json()) == 0:
        print("  ✓ User Isolation Active: Querying other user IDs returns empty dataset.")
    else:
        print("  ✗ User Isolation Leaked: Able to read another user's records.")

    # RAG Vector similarity search verification
    print("\n[5/8] Testing RAG Ingestion and Vector Search...")
    # Create test document
    doc_data = {
        "user_id": uid_a,
        "name": "Testing Manual",
        "file_path": "manual.txt",
        "file_type": "text/plain",
        "status": "processing"
    }
    r = requests.post(f"{SUPABASE_URL}/rest/v1/documents", json=doc_data, headers=headers_a)
    r = requests.get(f"{SUPABASE_URL}/rest/v1/documents?user_id=eq.{uid_a}", headers=headers_a)
    doc_id = r.json()[0]["id"]

    # Insert document chunk with 768 dimension mock vector
    mock_embedding = [0.1] * 768
    chunk_data = {
        "document_id": doc_id,
        "user_id": uid_a,
        "chunk_index": 0,
        "content": "Vocalis AI database system is powered by Supabase PostgreSQL.",
        "embedding": mock_embedding
    }
    r = requests.post(f"{SUPABASE_URL}/rest/v1/document_chunks", json=chunk_data, headers=headers_a)
    if r.status_code == 201 or r.status_code == 409: # 409 means already exists
        print("  ✓ Inserted document chunk with 768-dimension vector.")
    else:
        print(f"  ✗ Failed chunk insertion. Code: {r.status_code}, Body: {r.text}")

    # Query search_document_chunks PostgreSQL RPC
    search_payload = {
        "p_user_id": uid_a,
        "p_query_embedding": mock_embedding,
        "p_match_threshold": 0.8,
        "p_match_count": 5
    }
    r = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/search_document_chunks", json=search_payload, headers=headers_a)
    if r.status_code == 200:
        results = r.json()
        if len(results) > 0 and results[0]["chunk_index"] == 0:
            print(f"  ✓ Similarity search successful (Match Similarity: {results[0]['similarity']:.4f}).")
        else:
            print("  ✗ Similarity search returned no matches.")
    else:
        print(f"  ✗ Similarity search RPC failed. Code: {r.status_code}, Body: {r.text}")

    # Memory Vector Search Test
    print("\n[6/8] Testing Agent Memory and Semantic Retrieval...")
    memory_data = {
        "user_id": uid_a,
        "agent_id": agent_id,
        "memory_type": "fact",
        "content": "User prefers dark mode and neural voice in Hindi.",
        "embedding": mock_embedding,
        "importance": 0.95
    }
    r = requests.post(f"{SUPABASE_URL}/rest/v1/agent_memories", json=memory_data, headers=headers_a)
    if r.status_code == 201 or r.status_code == 409:
        print("  ✓ Inserted agent memory record.")
    else:
        print(f"  ✗ Failed memory insertion. Code: {r.status_code}, Body: {r.text}")

    # Query search_agent_memories PostgreSQL RPC
    search_mem_payload = {
        "p_agent_id": agent_id,
        "p_query_embedding": mock_embedding,
        "p_match_threshold": 0.8,
        "p_match_count": 5
    }
    r = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/search_agent_memories", json=search_mem_payload, headers=headers_a)
    if r.status_code == 200:
        results = r.json()
        if len(results) > 0:
            print(f"  ✓ Memory semantic search successful (Similarity: {results[0]['similarity']:.4f}).")
        else:
            print("  ✗ Memory semantic search returned no matches.")
    else:
        print(f"  ✗ Memory search RPC failed. Code: {r.status_code}, Body: {r.text}")

    # Task / Step Hierarchy Test
    print("\n[7/8] Testing Task / Step Hierarchy...")
    # Parent Task
    task_data = {
        "user_id": uid_a,
        "agent_id": agent_id,
        "title": "Main Task",
        "description": "Run tests and verify",
        "status": "executing",
        "priority": 1
    }
    r = requests.post(f"{SUPABASE_URL}/rest/v1/tasks", json=task_data, headers=headers_a)
    r = requests.get(f"{SUPABASE_URL}/rest/v1/tasks?user_id=eq.{uid_a}&parent_task_id=is.null", headers=headers_a)
    parent_task_id = r.json()[0]["id"]

    # Child Task
    subtask_data = {
        "user_id": uid_a,
        "agent_id": agent_id,
        "parent_task_id": parent_task_id,
        "title": "Subtask Research",
        "status": "completed",
        "priority": 0
    }
    r = requests.post(f"{SUPABASE_URL}/rest/v1/tasks", json=subtask_data, headers=headers_a)
    
    # Task Step
    step_data = {
        "task_id": parent_task_id,
        "step_number": 1,
        "description": "Execute database tests",
        "status": "completed"
    }
    r = requests.post(f"{SUPABASE_URL}/rest/v1/task_steps", json=step_data, headers=headers_a)
    if r.status_code == 201 or r.status_code == 409:
        print("  ✓ Created parent/child task hierarchy with step execution logs.")
    else:
        print(f"  ✗ Failed to create task step. Code: {r.status_code}, Body: {r.text}")

    # Approval and Action State Test
    print("\n[8/8] Testing Approvals Flow...")
    # Create tool execution log
    if tool_id:
        tool_exec_data = {
            "task_id": parent_task_id,
            "tool_id": tool_id,
            "agent_id": agent_id,
            "status": "queued",
            "input": {"filepath": "important_config.json"}
        }
        r = requests.post(f"{SUPABASE_URL}/rest/v1/tool_executions", json=tool_exec_data, headers=headers_a)
        r = requests.get(f"{SUPABASE_URL}/rest/v1/tool_executions?task_id=eq.{parent_task_id}", headers=headers_a)
        tool_exec_id = r.json()[0]["id"]

        # Create Approval Request (e.g. deleting or modifying files)
        approval_data = {
            "user_id": uid_a,
            "task_id": parent_task_id,
            "tool_execution_id": tool_exec_id,
            "action": "fs_delete",
            "risk_level": "high",
            "description": "Approve deletion of config file",
            "status": "pending"
        }
        r = requests.post(f"{SUPABASE_URL}/rest/v1/approvals", json=approval_data, headers=headers_a)
        r = requests.get(f"{SUPABASE_URL}/rest/v1/approvals?user_id=eq.{uid_a}&status=eq.pending", headers=headers_a)
        approval_id = r.json()[0]["id"]
        print("  ✓ Approval requested (Status: pending).")

        # Approve approval request
        r = requests.patch(f"{SUPABASE_URL}/rest/v1/approvals?id=eq.{approval_id}", json={"status": "approved", "resolved_at": "now()"}, headers=headers_a)
        r = requests.get(f"{SUPABASE_URL}/rest/v1/approvals?id=eq.{approval_id}", headers=headers_a)
        if r.json()[0]["status"] == "approved":
            print("  ✓ Approval transition verified (Status: approved).")
        else:
            print("  ✗ Approval transition failed.")
    else:
        print("  ✗ Tool ID not found, skipping tool execution / approval test.")

    print("\n" + "=" * 60)
    print("                TEST EXECUTION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
