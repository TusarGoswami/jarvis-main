import os
import re
import shutil
import subprocess
import time
import webbrowser
import psutil
import socket
import pygetwindow as gw
from urllib.parse import quote
import sqlite3

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

        # 2. Check Database custom commands
        try:
            con = _get_db()
            cursor = con.cursor()
            cursor.execute("SELECT path FROM sys_command WHERE LOWER(name) = ?", (cand,))
            sys_res = cursor.fetchall()
            if sys_res:
                os.startfile(sys_res[0][0])
                return {"status": "success", "action": "custom_sys_launched", "target": sys_res[0][0]}

            cursor.execute("SELECT url FROM web_command WHERE LOWER(name) = ?", (cand,))
            web_res = cursor.fetchall()
            if web_res:
                webbrowser.open(web_res[0][0])
                return {"status": "success", "action": "custom_web_opened", "url": web_res[0][0]}
        except Exception:
            pass

        # 3. Known apps
        if cand in KNOWN_APPS:
            try:
                os.startfile(KNOWN_APPS[cand])
                return {"status": "success", "action": "app_launched", "target": cand}
            except Exception as e:
                return {"status": "error", "message": str(e)}

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
                os.startfile(matched_val)
                return {"status": "success", "action": "fuzzy_app_launched", "target": matched_name}
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
            try:
                os.startfile(exe_path)
                return {"status": "success", "action": "path_app_launched", "target": cand}
            except Exception:
                pass

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
    clean = re.sub(r'^(play|bajao|on youtube|youtube pe|chalao)\s*', '', query, flags=re.I).strip()
    clean = re.sub(r'\s*(on youtube|youtube pe|youtube par)$', '', clean, flags=re.I).strip()
    if not clean:
        clean = query
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
            u = psutil.disk_usage(p.mountpoint)
            disks[p.device.replace('\\', '')] = round(u.percent, 1)
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
import pyautogui
pyautogui.FAILSAFE = True

def execute_gui_action(action_type: str, x: int = None, y: int = None, text: str = None, keys: list[str] = None) -> dict:
    """
    Executes a GUI action: click, type, hotkey, or scroll.
    x and y coordinates are target desktop coordinates.
    """
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

