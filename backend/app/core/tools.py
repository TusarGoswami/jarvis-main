import os
import re
import shutil
import subprocess
import time
import webbrowser
import psutil
import socket
from urllib.parse import quote
import sqlite3

IS_WINDOWS = platform.system() == "Windows"

# Platform-aware window manager
if IS_WINDOWS:
    try:
        import pygetwindow as gw
    except Exception:
        gw = None
else:
    gw = None

# Platform-aware GUI automation
if IS_WINDOWS or os.environ.get("DISPLAY"):
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
    except Exception:
        pyautogui = None
else:
    pyautogui = None

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(_BASE_DIR, "jarvis.db")

KNOWN_APPS = {
    'calculator': 'calc.exe',
    'notepad': 'notepad.exe',
    'paint': 'mspaint.exe',
    'cmd': 'cmd.exe',
    'command prompt': 'cmd.exe',
    'terminal': 'cmd.exe',
    'task manager': 'taskmgr.exe',
    'file explorer': 'explorer.exe',
    'explorer': 'explorer.exe',
    'settings': 'ms-settings:',
    'control panel': 'control',
    'snipping tool': 'snippingtool.exe',
    'word': 'winword.exe',
    'excel': 'excel.exe',
    'powerpoint': 'powerpnt.exe',
}

KNOWN_SITES = {
    'google': 'https://www.google.com',
    'youtube': 'https://www.youtube.com',
    'github': 'https://www.github.com',
    'gmail': 'https://mail.google.com',
    'chatgpt': 'https://chat.openai.com',
    'leetcode': 'https://www.leetcode.com',
    'facebook': 'https://www.facebook.com',
    'instagram': 'https://www.instagram.com',
    'twitter': 'https://www.twitter.com',
    'x': 'https://www.x.com',
    'linkedin': 'https://www.linkedin.com',
    'reddit': 'https://www.reddit.com',
    'amazon': 'https://www.amazon.in',
    'flipkart': 'https://www.flipkart.com',
    'spotify': 'https://open.spotify.com',
    'netflix': 'https://www.netflix.com',
    'whatsapp': 'https://web.whatsapp.com',
    'stackoverflow': 'https://stackoverflow.com',
    'wikipedia': 'https://www.wikipedia.org',
    'maps': 'https://maps.google.com',
    'drive': 'https://drive.google.com',
}

def _get_db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    return con

def _edit_distance(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]

def _fuzzy_match(name: str, max_dist: int = 2):
    best = None
    best_dist = max_dist + 1
    for key, val in KNOWN_APPS.items():
        d = _edit_distance(name, key)
        if d < best_dist:
            best_dist = d
            best = (key, val, 'app')
    for key, val in KNOWN_SITES.items():
        d = _edit_distance(name, key)
        if d < best_dist:
            best_dist = d
            best = (key, val, 'site')
    if best_dist <= max_dist:
        return best
    return None

def activate_window(search_term: str) -> bool:
    """Activates a window by search term on Windows if pygetwindow is available."""
    if not IS_WINDOWS or gw is None:
        return False
    try:
        windows = gw.getAllWindows()
        for win in windows:
            if win.title and search_term.lower() in win.title.lower():
                if win.isMinimized:
                    win.restore()
                win.activate()
                return True
    except Exception:
        pass
    return False

def _safe_start_target(target: str) -> bool:
    """Safely starts an application or file in a platform-compatible way."""
    if hasattr(os, "startfile"):
        try:
            os.startfile(target)
            return True
        except Exception:
            return False
    elif platform.system() == "Darwin":
        try:
            subprocess.Popen(["open", target])
            return True
        except Exception:
            return False
    else:
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            try:
                subprocess.Popen(["xdg-open", target])
                return True
            except Exception:
                return False
        return False

def launch_target(target: str) -> dict:
    target_clean = target.lower().strip()
    if not target_clean:
        return {"status": "error", "message": "Target name cannot be empty"}

    # Extract base app name if compound words like "and search", "and write" are attached
    split_match = re.split(r'\s+(and\s+(search|write|type|open|then|look)|aur|phir)\s+', target_clean)
    candidate_names = [target_clean]
    if split_match and split_match[0].strip() and split_match[0].strip() != target_clean:
        candidate_names.insert(0, split_match[0].strip())

    for cand in candidate_names:
        # 1. Check existing window
        if activate_window(cand):
            return {"status": "success", "action": "window_activated", "target": cand}

        # 1.5 Check Settings pages
        if "setting" in cand or cand in SETTINGS_PAGES:
            res = open_settings(cand)
            if res.get("status") == "success":
                return res

        # 2. Check Database custom commands
        try:
            con = _get_db()
            cursor = con.cursor()
            cursor.execute("SELECT path FROM sys_command WHERE LOWER(name) = ?", (cand,))
            sys_res = cursor.fetchall()
            if sys_res:
                if _safe_start_target(sys_res[0][0]):
                    return {"status": "success", "action": "custom_sys_launched", "target": sys_res[0][0]}
                return {"status": "error", "message": "This desktop automation operation is only available on Windows or environments with a desktop."}

            cursor.execute("SELECT url FROM web_command WHERE LOWER(name) = ?", (cand,))
            web_res = cursor.fetchall()
            if web_res:
                webbrowser.open(web_res[0][0])
                return {"status": "success", "action": "custom_web_opened", "url": web_res[0][0]}
        except Exception:
            pass

        # 3. Known apps
        if cand in KNOWN_APPS:
            if _safe_start_target(KNOWN_APPS[cand]):
                return {"status": "success", "action": "app_launched", "target": cand}
            if not IS_WINDOWS:
                return {"status": "error", "message": "This desktop automation operation is only available on Windows."}
            return {"status": "error", "message": f"Failed to launch application '{cand}'."}

        # 4. Known sites
        if cand in KNOWN_SITES:
            webbrowser.open(KNOWN_SITES[cand])
            return {"status": "success", "action": "site_opened", "target": KNOWN_SITES[cand]}

        # 5. Fuzzy match
        fuzzy = _fuzzy_match(cand)
        if fuzzy:
            matched_name, matched_val, match_type = fuzzy
            if activate_window(matched_name):
                return {"status": "success", "action": "fuzzy_window_activated", "target": matched_name}
            if match_type == 'app':
                if _safe_start_target(matched_val):
                    return {"status": "success", "action": "fuzzy_app_launched", "target": matched_name}
                if not IS_WINDOWS:
                    return {"status": "error", "message": "This desktop automation operation is only available on Windows."}
                return {"status": "error", "message": f"Failed to launch application '{matched_name}'."}
            else:
                webbrowser.open(matched_val)
                return {"status": "success", "action": "fuzzy_site_opened", "target": matched_val}

        # 6. Direct URL
        if '.' in cand or any(cand.endswith(t) for t in ['.com', '.org', '.net', '.in', '.io', '.dev', '.ai']):
            url = cand if cand.startswith("http") else f"https://{cand}"
            webbrowser.open(url)
            return {"status": "success", "action": "url_opened", "url": url}

        # 7. Safe PATH executable lookup using shutil.which
        exe_path = shutil.which(cand) or shutil.which(f"{cand}.exe")
        if exe_path:
            if _safe_start_target(exe_path):
                return {"status": "success", "action": "path_app_launched", "target": cand}

    # 8. Fallback to Google Search (No intrusive Windows popups)
    search_url = f"https://www.google.com/search?q={quote(target_clean)}"
    webbrowser.open(search_url)
    return {"status": "success", "action": "web_search_fallback", "query": target_clean}

def search_web(query: str) -> dict:
    url = f"https://www.google.com/search?q={quote(query)}"
    webbrowser.open(url)
    return {"status": "success", "action": "google_search", "query": query, "url": url}

def play_youtube(query: str) -> dict:
    # Clean query
    clean = re.sub(r'^(open youtube and |play|bajao|on youtube|youtube pe|chalao|listen to|search for|search)\s*', '', query, flags=re.I).strip()
    clean = re.sub(r'\s*(on youtube|youtube pe|youtube par)$', '', clean, flags=re.I).strip()
    if not clean:
        clean = query

    try:
        import pywhatkit
        pywhatkit.playonyt(clean)
        return {"status": "success", "action": "youtube_play", "query": clean}
    except Exception:
        url = f"https://www.youtube.com/results?search_query={quote(clean)}"
        webbrowser.open(url)
        return {"status": "success", "action": "youtube_play", "query": clean, "url": url}

def get_system_stats() -> dict:
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    net = psutil.net_io_counters()
    
    disks = {}
    for p in psutil.disk_partitions():
        try:
            device_key = p.device.replace('\\', '') if hasattr(p, 'device') else p.mountpoint
            u = psutil.disk_usage(p.mountpoint)
            disks[device_key] = round(u.percent, 1)
        except Exception:
            pass

    return {
        "cpu_percent": cpu,
        "ram_percent": ram.percent,
        "ram_used_gb": round(ram.used / (1024 ** 3), 2),
        "ram_total_gb": round(ram.total / (1024 ** 3), 2),
        "disks": disks,
        "net_sent_mb": round(net.bytes_sent / (1024 ** 2), 2),
        "net_recv_mb": round(net.bytes_recv / (1024 ** 2), 2),
        "battery": psutil.sensors_battery().percent if hasattr(psutil, "sensors_battery") and psutil.sensors_battery() else None,
        "timestamp": time.time()
    }

# --- GUI AUTOMATION & ACTION ENGINE ---
try:
    import pyautogui
    pyautogui.FAILSAFE = True
except Exception:
    pyautogui = None


def execute_gui_action(action_type: str, x: int = None, y: int = None, text: str = None, keys: list[str] = None) -> dict:
    """
    Executes a GUI action: click, type, hotkey, or scroll.
    x and y coordinates are target desktop coordinates.
    """
    if not pyautogui:
        return {"status": "error", "message": "GUI automation is unavailable in headless or non-display environment."}

    try:
        width, height = pyautogui.size()
        
        if action_type == "click" and x is not None and y is not None:
            target_x = max(0, min(width - 1, x))
            target_y = max(0, min(height - 1, y))
            pyautogui.moveTo(target_x, target_y, duration=0.4)
            pyautogui.click()
            return {"status": "success", "action": "click", "x": target_x, "y": target_y}
            
        elif action_type == "type" and text is not None:
            pyautogui.write(text, interval=0.03)
            return {"status": "success", "action": "type", "text": text}
            
        elif action_type == "hotkey" and keys is not None:
            pyautogui.hotkey(*keys)
            return {"status": "success", "action": "hotkey", "keys": keys}
            
        elif action_type == "scroll":
            amount = int(text) if text and text.isdigit() else 300
            pyautogui.scroll(amount)
            return {"status": "success", "action": "scroll", "amount": amount}
            
        return {"status": "error", "message": f"Invalid action parameters: {action_type}"}
    except Exception as e:
        return {"status": "error", "message": f"GUI execution failed: {str(e)}"}


def send_email(recipient_name: str, body: str) -> dict:
    """
    Looks up a contact's email from the database and opens the default mail client.
    """
    try:
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = con.cursor()
        cursor.execute("SELECT email, name FROM contacts WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?", ('%' + recipient_name.lower() + '%', recipient_name.lower() + '%'))
        res = cursor.fetchone()
        con.close()
        
        if not res or not res[0]:
            return {"status": "error", "message": f"Email contact for '{recipient_name}' not found."}
            
        recipient_email = res[0]
        name = res[1]
        
        # Construct standard mailto link
        subject = quote("Message from Assistant")
        mail_body = quote(body)
        mailto_url = f"mailto:{recipient_email}?subject={subject}&body={mail_body}"
        
        webbrowser.open(mailto_url)
        return {"status": "success", "action": "send_email", "recipient": name, "email": recipient_email}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- SYSTEM CONTROL TOOLS (Brightness, Windows Settings, Wi-Fi) ---

SETTINGS_PAGES = {
    'display': 'ms-settings:display',
    'screen': 'ms-settings:display',
    'sound': 'ms-settings:sound',
    'audio': 'ms-settings:sound',
    'volume': 'ms-settings:sound',
    'wifi': 'ms-settings:network-wifi',
    'wi-fi': 'ms-settings:network-wifi',
    'network': 'ms-settings:network',
    'internet': 'ms-settings:network',
    'bluetooth': 'ms-settings:bluetooth',
    'devices': 'ms-settings:bluetooth',
    'battery': 'ms-settings:batterysaver',
    'power': 'ms-settings:powersleep',
    'apps': 'ms-settings:appsfeatures',
    'applications': 'ms-settings:appsfeatures',
    'privacy': 'ms-settings:privacy',
    'security': 'ms-settings:privacy',
    'windows update': 'ms-settings:windowsupdate',
    'update': 'ms-settings:windowsupdate',
    'notifications': 'ms-settings:notifications',
    'personalization': 'ms-settings:personalization',
    'background': 'ms-settings:personalization-background',
    'colors': 'ms-settings:colors',
    'date': 'ms-settings:dateandtime',
    'time': 'ms-settings:dateandtime',
}

def set_brightness(level: int) -> dict:
    """
    Sets display brightness to an absolute percentage (0-100).
    Clamps values outside 0-100.
    """
    try:
        import screen_brightness_control as sbc
        clamped_level = max(0, min(100, int(level)))
        sbc.set_brightness(clamped_level)
        current = sbc.get_brightness()
        actual = current[0] if isinstance(current, list) and current else clamped_level
        print(f"[Activity] Brightness set to {actual}%")
        return {
            "status": "success",
            "action": "set_brightness",
            "level": actual,
            "message": f"Brightness set to {actual}%."
        }
    except Exception as e:
        err_msg = str(e)
        if "NoDisplayError" in err_msg or "failed to find any display" in err_msg.lower() or "unsupported" in err_msg.lower():
            msg = "Brightness control is not supported on this display hardware or virtual environment."
        else:
            msg = f"Failed to set brightness: {err_msg}"
        return {"status": "error", "action": "set_brightness", "message": msg}


def adjust_brightness(delta: int = 10) -> dict:
    """
    Adjusts display brightness relatively by +/- delta percentage.
    """
    try:
        import screen_brightness_control as sbc
        current_list = sbc.get_brightness()
        curr = current_list[0] if isinstance(current_list, list) and current_list else 50
        new_level = max(0, min(100, curr + int(delta)))
        sbc.set_brightness(new_level)
        direction = "increased" if delta >= 0 else "decreased"
        print(f"[Activity] Brightness {direction} to {new_level}%")
        return {
            "status": "success",
            "action": "adjust_brightness",
            "level": new_level,
            "delta": delta,
            "message": f"Brightness {direction} to {new_level}%."
        }
    except Exception as e:
        err_msg = str(e)
        if "NoDisplayError" in err_msg or "failed to find any display" in err_msg.lower():
            msg = "Brightness adjustment is not supported on this display hardware."
        else:
            msg = f"Failed to adjust brightness: {err_msg}"
        return {"status": "error", "action": "adjust_brightness", "message": msg}


def open_settings(page: str = None) -> dict:
    """
    Opens Windows Settings, optionally navigating to a specific subpage via ms-settings URI.
    """
    if not IS_WINDOWS:
        return {
            "status": "error",
            "action": "open_settings",
            "message": "This desktop automation operation is only available on Windows."
        }
    try:
        clean_page = page.strip().lower() if page else None
        uri = "ms-settings:"
        note = None

        if clean_page:
            found_uri = None
            for key, val in SETTINGS_PAGES.items():
                if key in clean_page or clean_page in key:
                    found_uri = val
                    clean_page = key
                    break
            if found_uri:
                uri = found_uri
            else:
                note = f"Specific page '{page}' not found; opened main Settings instead."

        # Launch via os.startfile with cmd /c start fallback
        if hasattr(os, "startfile"):
            try:
                os.startfile(uri)
            except Exception:
                try:
                    subprocess.Popen(["cmd", "/c", "start", uri], shell=True)
                except Exception:
                    subprocess.Popen(["explorer.exe", uri])
        else:
            subprocess.Popen(["cmd", "/c", "start", uri], shell=True)

        # Attempt to bring Settings window to focus
        if gw is not None:
            try:
                time.sleep(0.3)
                for w in gw.getAllWindows():
                    if w.title and "setting" in w.title.lower():
                        if w.isMinimized:
                            w.restore()
                        win_activate = getattr(w, "activate", None)
                        if win_activate:
                            win_activate()
                        break
            except Exception:
                pass

        target_name = clean_page if clean_page and not note else "general"
        print(f"[Activity] Opened Settings ({target_name})")
        msg = f"Opened Windows Settings ({target_name})." if not note else note
        return {
            "status": "success",
            "action": "open_settings",
            "page": target_name,
            "uri": uri,
            "message": msg
        }
    except Exception as e:
        return {"status": "error", "action": "open_settings", "message": f"Failed to open Settings: {str(e)}"}


def set_wifi_state(enabled: bool) -> dict:
    """
    Toggles the Wi-Fi network interface on Windows (admin=enabled/disabled).
    Gracefully detects current state (no-op if already in state) and catches permission failures.
    """
    if not IS_WINDOWS:
        return {
            "status": "error",
            "action": "set_wifi_state",
            "message": "This desktop automation operation is only available on Windows."
        }
    try:
        target_state = "enabled" if enabled else "disabled"
        state_label = "on" if enabled else "off"

        # 1. Check current Wi-Fi adapter state
        try:
            check_proc = subprocess.run(
                ["netsh", "interface", "show", "interface"],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = check_proc.stdout

            is_already_state = False
            for line in output.splitlines():
                line_lower = line.lower()
                if "wi-fi" in line_lower or "wireless" in line_lower or "wlan" in line_lower:
                    if target_state in line_lower:
                        is_already_state = True
                    break

            if is_already_state:
                return {
                    "status": "success",
                    "action": "set_wifi_state",
                    "enabled": enabled,
                    "noop": True,
                    "message": f"Wi-Fi is already {state_label}."
                }
        except Exception:
            pass

        # 2. Attempt to toggle Wi-Fi
        set_proc = subprocess.run(
            ["netsh", "interface", "set", "interface", "Wi-Fi", f"admin={target_state}"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if set_proc.returncode != 0:
            err_text = (set_proc.stderr or set_proc.stdout or "").strip()
            err_lower = err_text.lower()
            if (
                "administrator" in err_lower
                or "elevation" in err_lower
                or "access is denied" in err_lower
                or "privilege" in err_lower
                or set_proc.returncode == 1
            ):
                print(f"[Activity] Wi-Fi toggle failed: insufficient privileges")
                return {
                    "status": "error",
                    "action": "set_wifi_state",
                    "permission_error": True,
                    "message": "Wi-Fi couldn't be toggled — this requires running Vocalis as Administrator."
                }
            return {
                "status": "error",
                "action": "set_wifi_state",
                "message": f"Failed to toggle Wi-Fi: {err_text}"
            }

        print(f"[Activity] Wi-Fi turned {state_label}")
        return {
            "status": "success",
            "action": "set_wifi_state",
            "enabled": enabled,
            "message": f"Wi-Fi has been turned {state_label}."
        }

    except Exception as e:
        return {
            "status": "error",
            "action": "set_wifi_state",
            "message": f"Wi-Fi control encountered an unexpected error: {str(e)}"
        }
