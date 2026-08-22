import pytest
import json
import os
from unittest.mock import patch, MagicMock

from app.core.email_tool import (
    validate_email_format,
    auto_generate_subject,
    parse_email_command,
    format_email_confirmation_reason,
    send_email,
    email_rate_limiter,
    save_gmail_credentials,
    load_gmail_credentials,
    GMAIL_TOKEN_PATH
)
from app.core.guardrails import evaluate_guardrails
from app.core.agent import process_turn
from app.core.tools_registry import TOOLS_MANIFEST, execute_tool
from engine.vault import decrypt_data

# ==================== EMAIL CAPABILITY TEST SUITE ====================

# 1. Format Validation Tests
def test_email_format_validation_valid():
    valid_addresses = [
        "hridayeshdebsarma@gmail.com",
        "john@example.com",
        "sarah@company.co.uk",
        "alex.smith+work@domain.io",
        "first.last_name@sub.domain.org"
    ]
    for email in valid_addresses:
        assert validate_email_format(email) is True, f"Failed for valid email: {email}"

def test_email_format_validation_invalid():
    invalid_addresses = [
        "",
        "plainaddress",
        "@missingusername.com",
        "username@.com",
        "username@com",
        "user space@domain.com",
        None
    ]
    for email in invalid_addresses:
        assert validate_email_format(email) is False, f"Should fail for invalid email: {email}"


# 2. Command Parsing Tests
def test_email_command_parsing_saying_pattern():
    cmd = "Send a mail to hridayeshdebsarma@gmail.com saying honesty is the best policy"
    parsed = parse_email_command(cmd)
    assert parsed["to"] == "hridayeshdebsarma@gmail.com"
    assert "honesty is the best policy" in parsed["body"].lower()
    assert parsed["subject"] is not None
    assert "honesty" in parsed["subject"].lower()

def test_email_command_parsing_multiple_recipients():
    cmd = "Send a mail to hridayeshdebsarma6@gmail.com and tusargoswami0027@gmail.com and adarshyadav3924@gmail.com saying honesty is the best policy"
    parsed = parse_email_command(cmd)
    assert "hridayeshdebsarma6@gmail.com" in parsed["to"]
    assert "tusargoswami0027@gmail.com" in parsed["to"]
    assert "adarshyadav3924@gmail.com" in parsed["to"]
    assert "honesty is the best policy" in parsed["body"].lower()
    assert parsed["subject"] is not None

def test_email_command_parsing_with_explicit_subject():
    cmd = "Email john@example.com with subject 'Meeting notes' and tell him the meeting is moved to 3pm"
    parsed = parse_email_command(cmd)
    assert parsed["to"] == "john@example.com"
    assert parsed["subject"] == "Meeting notes"
    assert "meeting is moved to 3pm" in parsed["body"]

def test_email_command_parsing_colon_pattern():
    cmd = "Send an email to sarah@company.com: the report is attached, let me know if you have questions"
    parsed = parse_email_command(cmd)
    assert parsed["to"] == "sarah@company.com"
    assert "the report is attached" in parsed["body"]
    assert parsed["subject"] is not None

def test_email_command_parsing_missing_recipient():
    cmd = "Send an email saying I will be late today"
    parsed = parse_email_command(cmd)
    assert parsed["to"] is None
    assert "late today" in parsed["body"]

def test_auto_generate_subject():
    body = "the quarterly earnings report is ready for your review"
    subject = auto_generate_subject(body)
    assert subject.startswith("The")
    assert len(subject.split()) <= 7


# 3. Guardrails Confirmation Gate Tests
def test_guardrails_email_confirmation_enforced():
    safe, reason = evaluate_guardrails(
        intent="send_email",
        action_data={"to": "hridayeshdebsarma@gmail.com", "subject": "Test", "body": "Honesty is the best policy"},
        confidence=0.99,
        tool_name="send_email",
        tool_args={"to": "hridayeshdebsarma@gmail.com", "subject": "Test", "body": "Honesty is the best policy"}
    )
    assert safe is False
    assert "CONFIRM ACTION: Send Email" in reason
    assert "To: hridayeshdebsarma@gmail.com" in reason
    assert "Honesty is the best policy" in reason

def test_tools_manifest_send_email_security_settings():
    assert "send_email" in TOOLS_MANIFEST
    tool = TOOLS_MANIFEST["send_email"]
    assert tool.risk_level == "high"
    assert tool.requires_approval is True
    assert "to" in tool.parameters["properties"]


# 4. Agent Interactive Confirmation and Clarification Tests
@pytest.mark.asyncio
async def test_agent_email_clarifying_question_when_recipient_missing():
    res = await process_turn("send an email saying the meeting is postponed", allow_actions=False)
    assert res.intent == "send_email"
    assert "who would you like me to send" in res.reply_text.lower() or "recipient" in res.reply_text.lower()
    assert res.needs_confirmation is False

@pytest.mark.asyncio
async def test_agent_email_triggers_confirmation_card():
    cmd = "Send a mail to hridayeshdebsarma@gmail.com saying honesty is the best policy"
    res = await process_turn(cmd, allow_actions=False)
    assert res.intent == "send_email"
    assert res.needs_confirmation is True
    assert res.confirmation_reason is not None
    assert "hridayeshdebsarma@gmail.com" in res.confirmation_reason
    assert "honesty is the best policy" in res.confirmation_reason.lower()


# 5. Rate Limiting Tests
def test_email_rate_limiter():
    email_rate_limiter.reset()
    
    # 5 sends should be allowed
    for _ in range(5):
        can_send, _ = email_rate_limiter.can_send()
        assert can_send is True
        email_rate_limiter.record_send()

    # 6th send must be blocked
    can_send, err = email_rate_limiter.can_send()
    assert can_send is False
    assert "rate limit exceeded" in err.lower()
    
    email_rate_limiter.reset()


# 6. OAuth Token Encryption at Rest Tests
def test_oauth_token_encrypted_storage(tmp_path):
    test_refresh_token = "1//0gFAKE_REFRESH_TOKEN_GMAIL_OAUTH_TEST_12345"
    test_client_id = "test_client_id_123.apps.googleusercontent.com"
    test_client_secret = "GOCSPX-test_client_secret_xyz"

    test_token_file = str(tmp_path / "test_gmail_token.json")
    save_gmail_credentials(test_refresh_token, test_client_id, test_client_secret, token_path=test_token_file)

    assert os.path.exists(test_token_file)
    with open(test_token_file, "r", encoding="utf-8") as f:
        stored_data = json.load(f)

    # Assert raw secrets are NOT in plaintext on disk
    assert test_refresh_token not in stored_data["refresh_token"]
    assert stored_data["refresh_token"].startswith("enc::")
    assert test_client_secret not in stored_data["client_secret"]
    assert stored_data["client_secret"].startswith("enc::")

    # Assert decryption works correctly
    creds = load_gmail_credentials(token_path=test_token_file)
    assert creds is not None
    assert creds.refresh_token == test_refresh_token


# 7. Mocked Gmail API Send Execution Tests
def test_send_email_mocked_success():
    email_rate_limiter.reset()
    mock_service = MagicMock()
    mock_messages = MagicMock()
    mock_send = MagicMock()
    mock_send.execute.return_value = {"id": "18f0a1b2c3d4e5f6"}
    mock_messages.send.return_value = mock_send
    mock_service.users.return_value.messages.return_value = mock_messages

    with patch("app.core.email_tool.get_gmail_service", return_value=mock_service):
        res = send_email(
            to="hridayeshdebsarma@gmail.com",
            subject="Test Subject",
            body="Honesty is the best policy"
        )
        assert res["status"] == "success"
        assert res["message_id"] == "18f0a1b2c3d4e5f6"
        assert res["to"] == "hridayeshdebsarma@gmail.com"
        mock_messages.send.assert_called_once()


def test_send_email_invalid_recipient_error():
    res = send_email(to="not-an-email", body="Hello")
    assert res["status"] == "error"
    assert "Invalid recipient email format" in res["message"]


def test_send_email_sanitized_api_error():
    email_rate_limiter.reset()
    with patch("app.core.email_tool.get_gmail_service", side_effect=Exception("API failure: key=AIzaSyFAKEKEY12345678901234567890 failed")):
        res = send_email(to="user@example.com", body="Hello")
        assert res["status"] == "error"
        assert "AIzaSyFAKEKEY" not in res["message"]
        assert "[REDACTED_GEMINI_KEY]" in res["message"]


@pytest.mark.asyncio
async def test_agent_execute_authorized_action_flow():
    mock_service = MagicMock()
    mock_messages = MagicMock()
    mock_send = MagicMock()
    mock_send.execute.return_value = {"id": "auth_msg_999"}
    mock_messages.send.return_value = mock_send
    mock_service.users.return_value.messages.return_value = mock_messages

    with patch("app.core.email_tool.get_gmail_service", return_value=mock_service):
        # 1. First trigger confirmation
        res1 = await process_turn("Send a mail to hridayeshdebsarma@gmail.com saying honesty is the best policy", allow_actions=False)
        assert res1.needs_confirmation is True
        assert "Ready to send email" in res1.reply_text

        # 2. Then send authorization command
        res2 = await process_turn("Execute authorized action", allow_actions=True)
        assert res2.intent == "send_email"
        assert "Email successfully sent" in res2.reply_text
        assert len(res2.actions_executed) > 0
        assert res2.actions_executed[0].get("message_id") == "auth_msg_999"
