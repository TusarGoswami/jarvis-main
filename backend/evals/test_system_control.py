import os
import sys
import subprocess
import pytest
from unittest.mock import patch, MagicMock

# Ensure backend root is in pythonpath
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.tools import (
    set_brightness,
    adjust_brightness,
    open_settings,
    set_wifi_state,
    SETTINGS_PAGES
)


# ==============================================================================
# 1. BRIGHTNESS CONTROL TESTS
# ==============================================================================

@patch("screen_brightness_control.set_brightness")
@patch("screen_brightness_control.get_brightness")
def test_brightness_value_clamping(mock_get, mock_set):
    mock_get.return_value = [50]
    
    # Test upper clamp
    res_high = set_brightness(level=150)
    assert res_high["status"] == "success"
    mock_set.assert_called_with(100)

    # Test lower clamp
    res_low = set_brightness(level=-30)
    assert res_low["status"] == "success"
    mock_set.assert_called_with(0)


@patch("screen_brightness_control.set_brightness")
@patch("screen_brightness_control.get_brightness")
def test_brightness_relative_adjustment(mock_get, mock_set):
    mock_get.return_value = [40]

    # Increase brightness by 20 -> 60
    res_inc = adjust_brightness(delta=20)
    assert res_inc["status"] == "success"
    assert res_inc["level"] == 60
    mock_set.assert_called_with(60)

    # Decrease brightness by 50 -> clamped to 0
    res_dec = adjust_brightness(delta=-50)
    assert res_dec["status"] == "success"
    assert res_dec["level"] == 0
    mock_set.assert_called_with(0)


@patch("screen_brightness_control.set_brightness", side_effect=Exception("NoDisplayError: failed to find any display"))
def test_brightness_unsupported_hardware_mocked(mock_set):
    res = set_brightness(level=70)
    assert res["status"] == "error"
    assert "not supported on this display hardware" in res["message"]


# ==============================================================================
# 2. OPEN WINDOWS SETTINGS TESTS
# ==============================================================================

@patch("os.startfile")
def test_settings_known_pages_mapping(mock_startfile):
    # Test Display
    res_disp = open_settings(page="display")
    assert res_disp["status"] == "success"
    assert res_disp["uri"] == "ms-settings:display"
    mock_startfile.assert_called_with("ms-settings:display")

    # Test Wi-Fi
    res_wifi = open_settings(page="wifi")
    assert res_wifi["status"] == "success"
    assert res_wifi["uri"] == "ms-settings:network-wifi"

    # Test Bluetooth
    res_bt = open_settings(page="bluetooth")
    assert res_bt["status"] == "success"
    assert res_bt["uri"] == "ms-settings:bluetooth"

    # Test Sound
    res_snd = open_settings(page="sound")
    assert res_snd["status"] == "success"
    assert res_snd["uri"] == "ms-settings:sound"


@patch("os.startfile")
def test_settings_unknown_page_fallback(mock_startfile):
    res_unknown = open_settings(page="quantum-teleportation-settings")
    assert res_unknown["status"] == "success"
    assert res_unknown["uri"] == "ms-settings:"
    assert "opened main Settings instead" in res_unknown["message"]
    mock_startfile.assert_called_with("ms-settings:")


# ==============================================================================
# 3. WI-FI STATE TOGGLE TESTS
# ==============================================================================

@patch("subprocess.run")
def test_wifi_already_in_state_noop(mock_run):
    # Mock netsh interface show interface returning Wi-Fi enabled
    mock_check = MagicMock()
    mock_check.stdout = (
        "Admin State    State          Type             Interface Name\n"
        "-------------------------------------------------------------------------\n"
        "Enabled        Connected      Dedicated        Wi-Fi\n"
    )
    mock_run.return_value = mock_check

    # Calling turn on when already on -> noop
    res = set_wifi_state(enabled=True)
    assert res["status"] == "success"
    assert res.get("noop") is True
    assert "Wi-Fi is already on" in res["message"]


@patch("subprocess.run")
def test_wifi_permission_failure_graceful_message(mock_run):
    # First call: show interface (shows disabled)
    mock_check = MagicMock()
    mock_check.stdout = "Disabled       Disconnected   Dedicated        Wi-Fi\n"

    # Second call: set interface fails with access denied
    mock_fail = MagicMock()
    mock_fail.returncode = 1
    mock_fail.stderr = "An error occurred: Access is denied. Elevation required."
    mock_fail.stdout = ""

    mock_run.side_effect = [mock_check, mock_fail]

    res = set_wifi_state(enabled=True)
    assert res["status"] == "error"
    assert res.get("permission_error") is True
    assert "requires running Vocalis as Administrator" in res["message"]


@patch("subprocess.run")
def test_wifi_toggle_success_mocked(mock_run):
    # First call: show interface (shows disabled)
    mock_check = MagicMock()
    mock_check.stdout = "Disabled       Disconnected   Dedicated        Wi-Fi\n"

    # Second call: set interface succeeds
    mock_ok = MagicMock()
    mock_ok.returncode = 0
    mock_ok.stderr = ""
    mock_ok.stdout = ""

    mock_run.side_effect = [mock_check, mock_ok]

    res = set_wifi_state(enabled=True)
    assert res["status"] == "success"
    assert "Wi-Fi has been turned on" in res["message"]


# ==============================================================================
# 4. COMPOUND VOICE COMMAND ROUTING TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_compound_youtube_play_routing():
    from app.core.agent import process_turn
    with patch("app.core.tools.webbrowser.open") as mock_open:
        resp = await process_turn("open youtube and play ramayana trailer")
        assert resp.intent == "youtube"
        assert "Playing ramayana trailer on YouTube." in resp.reply_text
        assert any(a.get("action") == "youtube_play" for a in resp.actions_executed)


@pytest.mark.asyncio
async def test_compound_open_settings_routing():
    from app.core.agent import process_turn
    with patch("os.startfile") as mock_startfile:
        resp = await process_turn("open display settings")
        assert resp.intent == "open_settings"
        assert "Opened Windows Settings (display)." in resp.reply_text
        mock_startfile.assert_called_with("ms-settings:display")
