import os
from urllib.parse import quote
import sqlite3
import subprocess
import time
import webbrowser
import pygame
import eel
import pyaudio
import pyautogui
import pygetwindow as gw
from engine.speech import speak

from engine.config import ASSISTANT_NAME, GEMINI_API_KEY
import pywhatkit as kit

from engine.helper import extract_yt_term, remove_words
from google import genai
import engine.db

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con = sqlite3.connect(os.path.join(_BASE_DIR, "jarvis.db"), check_same_thread=False)
cursor = con.cursor()

# Initialize pygame mixer for non-blocking sound playback
pygame.mixer.init()

@eel.expose
def playAssistantSound():
    music_dir = os.path.join(_BASE_DIR, "www", "assets", "audio", "start_sound.mp3")
    try:
        pygame.mixer.music.load(music_dir)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"playAssistantSound error: {e}")

    
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
    'whatsapp web': 'https://web.whatsapp.com',
    'stackoverflow': 'https://stackoverflow.com',
    'stack overflow': 'https://stackoverflow.com',
    'wikipedia': 'https://www.wikipedia.org',
    'maps': 'https://maps.google.com',
    'google maps': 'https://maps.google.com',
    'drive': 'https://drive.google.com',
    'google drive': 'https://drive.google.com',
}


def _editDistance(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i-1] == b[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    return dp[m][n]


def _fuzzyMatch(name, max_dist=2):
    best = None
    best_dist = max_dist + 1
    for key, val in KNOWN_APPS.items():
        d = _editDistance(name, key)
        if d < best_dist:
            best_dist = d
            best = (key, val, 'app')
    for key, val in KNOWN_SITES.items():
        d = _editDistance(name, key)
        if d < best_dist:
            best_dist = d
            best = (key, val, 'site')
    if best_dist <= max_dist:
        return best
    return None


def _activateWindow(search_term):
    """Try to find and activate an existing window with a partial title match."""
    windows = gw.getAllWindows()
    for win in windows:
        if win.title and search_term.lower() in win.title.lower():
            try:
                if win.isMinimized:
                    win.restore()
                win.activate()
                return True
            except Exception:
                # Sometimes activation fails if window is in a transitional state
                pass
    return False


def openCommand(query):
    q = query.lower()
    q = q.replace(ASSISTANT_NAME.lower(), "")
    q = q.replace("open", "")
    app_name = q.strip()

    if app_name == "":
        return

    try:
        # Check if already running as a window first
        if _activateWindow(app_name):
            speak(f"Switching to existing {app_name} session, Sir.")
            return

        cursor.execute(
            'SELECT path FROM sys_command WHERE LOWER(name) = ?', (app_name.lower(),))
        results = cursor.fetchall()

        if len(results) != 0:
            speak("Opening " + app_name + ", Sir.")
            os.startfile(results[0][0])
            return

        cursor.execute(
            'SELECT url FROM web_command WHERE LOWER(name) = ?', (app_name.lower(),))
        results = cursor.fetchall()

        if len(results) != 0:
            url = results[0][0]
            # Extra check for sites: title usually contains domain or name
            if _activateWindow(app_name):
                speak(f"Switching to your existing {app_name} tab, Sir.")
                return
            speak("Opening " + app_name + " in a new tab, Sir.")
            webbrowser.open(url)
            return

        if app_name in KNOWN_APPS:
            speak("Launching " + app_name + ", Sir.")
            os.startfile(KNOWN_APPS[app_name])
            return

        if app_name in KNOWN_SITES:
            if _activateWindow(app_name):
                speak(f"Bringing your {app_name} tab to the front, Sir.")
                return
            speak("Opening " + app_name + ", Sir.")
            webbrowser.open(KNOWN_SITES[app_name])
            return

        # Fuzzy match check
        fuzzy_match = _fuzzyMatch(app_name)
        if fuzzy_match:
            matched_name, matched_val, match_type = fuzzy_match
            if _activateWindow(matched_name):
                speak(f"Switching to your {matched_name} session, Sir.")
                return
            speak("Opening " + matched_name + ", Sir.")
            if match_type == 'app':
                os.startfile(matched_val)
            else:
                webbrowser.open(matched_val)
            return

        # URL detection
        if '.' in app_name or any(app_name.endswith(t) for t in ['.com', '.in', '.org', '.net', '.io', '.me']):
            # For sites like whatsapp.com, check if 'whatsapp' window exists
            name_part = app_name.split('.')[0]
            if _activateWindow(name_part):
                speak(f"Switching to existing {name_part} tab, Sir.")
                return
            speak("Opening " + app_name + ", Sir.")
            url = app_name if app_name.startswith('http') else 'https://' + app_name
            webbrowser.open(url)
            return

        # Final local app/search fallback
        speak("Attempting to open " + app_name + ", Sir.")
        try:
            # Use subprocess to avoid blocking and capture errors silently
            result = subprocess.run(
                f'start "" "{app_name}"', shell=True,
                capture_output=True, timeout=3
            )
            if result.returncode != 0:
                raise Exception("Not found")
        except Exception:
            speak("I couldn't find that locally, Sir. Searching the web.")
            webbrowser.open("https://www.google.com/search?q=" + app_name.replace(' ', '+'))

    except Exception as e:
        print("openCommand error:", e)
        speak("I encountered an issue, Sir. Let me search the web instead.")
        webbrowser.open("https://www.google.com/search?q=" + app_name.replace(' ', '+'))

       

def PlayYoutube(query):
    search_term = extract_yt_term(query)
    if search_term:
        speak(f"Playing {search_term} on YouTube")
        kit.playonyt(search_term)
    else:
        speak("What should I play on YouTube, Sir?")




# find contacts
def findContact(query):
    
    words_to_remove = [ASSISTANT_NAME.lower(), 'make', 'a', 'to', 'phone', 'call', 'send', 'message', 'whatsapp', 'video']
    query = remove_words(query, words_to_remove)

    try:
        query = query.strip().lower()
        cursor.execute("SELECT mobile_no FROM contacts WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?", ('%' + query + '%', query + '%'))
        results = cursor.fetchall()

        if not results:
            speak(f'Contact {query} not found in your database, Sir.')
            return 0, 0
            
        mobile_number_str = str(results[0][0])

        if not mobile_number_str.startswith('+91'):
            mobile_number_str = '+91' + mobile_number_str

        return mobile_number_str, query
    except Exception as e:
        speak('not exist in contacts')
        return 0, 0
    
def whatsApp(mobile_no, message, flag, name):
    

    if flag == 'message':
        target_tab = 12
        jarvis_message = "message send successfully to "+name

    elif flag == 'call':
        target_tab = 7
        message = ''
        jarvis_message = "calling to "+name

    else:
        target_tab = 6
        message = ''
        jarvis_message = "starting video call with "+name


    # Encode the message for URL
    encoded_message = quote(message)
    print(encoded_message)
    # Construct the URL
    whatsapp_url = f"whatsapp://send?phone={mobile_no}&text={encoded_message}"

    # Construct the full command
    full_command = f'start "" "{whatsapp_url}"'

    # Open WhatsApp with the constructed URL using cmd.exe
    subprocess.run(full_command, shell=True)
    time.sleep(5)
    
    pyautogui.hotkey('ctrl', 'f')

    for _ in range(1, target_tab):
        pyautogui.hotkey('tab')

    pyautogui.hotkey('enter')
    speak(jarvis_message)

# chat bot
_gemini_client = None
_conversation_history = []
MAX_HISTORY_TURNS = 10

JARVIS_PERSONA = (
    "You are JARVIS, an intelligent personal AI assistant created by Tusar. "
    "You are confident, calm, helpful, and slightly futuristic in tone — like Tony Stark's JARVIS. "
    "You address the user as 'Sir'. If asked who you are or who made you, say you are JARVIS created by Tusar. "
    "Keep responses short (2-3 sentences max), natural, and conversational. Never be robotic. "
    "If the user asks for real-time info like time or date, tell them you can check it with your system tools."
)

LANG_INSTRUCTIONS = {
    'hi': JARVIS_PERSONA + " The user is speaking in Hindi. You MUST respond ONLY in Hindi (Devanagari script). Do not use English words unless absolutely necessary.",
    'bn': JARVIS_PERSONA + " The user is speaking in Bengali. You MUST respond ONLY in Bengali (Bengali script). Do not use English words unless absolutely necessary.",
    'en': JARVIS_PERSONA + " Respond in English.",
}


def chatBot(query, lang='en'):
    global _gemini_client, _conversation_history
    user_input = query.lower()
    system_prompt = LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS['en'])

    try:
        if not GEMINI_API_KEY:
            speak("Sir, my Gemini brain is not configured. Please add an API key.")
            return "Key missing"

        try:
            eel.showThinking()
        except Exception:
            pass

        if _gemini_client is None:
            _gemini_client = genai.Client(api_key=GEMINI_API_KEY)

        # Build prompt with system instructions + conversation history + current user input
        prompt_parts = [system_prompt]
        for turn in _conversation_history:
            prompt_parts.append(f"User: {turn['user']}")
            prompt_parts.append(f"JARVIS: {turn['model']}")
        prompt_parts.append(f"User: {user_input}")

        full_prompt = "\n\n".join(prompt_parts)

        response = _gemini_client.models.generate_content(
            model='gemini-3.5-flash',
            contents=full_prompt
        )
        response_text = response.text

        # Append to history
        _conversation_history.append({'user': user_input, 'model': response_text})
        if len(_conversation_history) > MAX_HISTORY_TURNS:
            _conversation_history.pop(0)

        print(response_text)
        speak(response_text, lang)
        return response_text

    except Exception as e:
        print(e)
        if lang == 'hi':
            speak("माफ कीजिये, अभी मेरे Gemini से कनेक्शन में दिक्कत है।", 'hi')
        elif lang == 'bn':
            speak("মাফ করবেন, এখন আমার Gemini সংযোগে সমস্যা হচ্ছে।", 'bn')
        else:
            speak("I'm having trouble connecting to my Gemini brain right now.")
        return str(e)

# android automation

def makeCall(name, mobileNo):
    mobileNo =mobileNo.replace(" ", "")
    speak("Calling "+name)
    command = 'adb shell am start -a android.intent.action.CALL -d tel:'+mobileNo
    os.system(command)


# to send message
def sendMessage(message, mobileNo, name):
    from engine.helper import replace_spaces_with_percent_s, goback, keyEvent, tapEvents, adbInput
    message = replace_spaces_with_percent_s(message)
    mobileNo = replace_spaces_with_percent_s(mobileNo)
    speak("sending message")
    goback(4)
    time.sleep(1)
    keyEvent(3)
    # open sms app
    tapEvents(136, 2220)
    #start chat
    tapEvents(819, 2192)
    # search mobile no
    adbInput(mobileNo)
    #tap on name
    tapEvents(601, 574)
    # tap on input
    tapEvents(390, 2270)
    #message
    adbInput(message)
    #send
    tapEvents(957, 1397)
    speak("message send successfully to "+name)