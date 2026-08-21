import speech_recognition as sr
import eel
import time
import re
import os
import webbrowser
from datetime import datetime
import json
import psutil
import socket

from engine.speech import speak, detectLanguage, detectTargetLanguage


# ==================== SPEECH RECOGNITION ====================
def takecommand():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print('listening....')
            eel.DisplayMessage('listening....')
            r.pause_threshold = 1
            r.adjust_for_ambient_noise(source, duration=0.8)
            if r.energy_threshold < 300:
                r.energy_threshold = 300
            print(f"Adjusted Energy threshold: {r.energy_threshold}")
            audio = r.listen(source, timeout=10, phrase_time_limit=6)

        print('recognizing...')
        eel.DisplayMessage('recognizing....')

        try:
            query = r.recognize_google(audio, language='en-in')
        except sr.UnknownValueError:
            print("English recognition failed, trying Hindi...")
            try:
                query = r.recognize_google(audio, language='hi-IN')
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio in English or Hindi")
                return ""

        print(f"user said: {query}")
        eel.DisplayMessage(query)
        return query.lower()

    except sr.WaitTimeoutError:
        print("Listening timed out — no speech detected. Please try again.")
        eel.DisplayMessage("Listening timed out. Please try again.")
        return ""
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return ""
    except Exception as e:
        print(f"takecommand error: {e}")
        return ""



# ==================== COMMAND SPLITTING ====================
def splitCompoundCommand(query):
    splitters = [' and also ', ' and then ', ' also ', ' aur ', ' then ', ' and ']
    parts = [query]
    for splitter in splitters:
        new_parts = []
        for part in parts:
            new_parts.extend(part.split(splitter))
        parts = new_parts
    return [p.strip() for p in parts if p.strip()]


# ==================== INTENT CLASSIFICATION ====================
def classifyIntent(query):
    q = query.lower().strip()

    # Identity
    identity_patterns = [
        'who are you', 'who r u', 'what are you', 'what is your name',
        'whats your name', "what's your name", 'tell me your name', 
        'your name', 'kya naam', 'kaun ho',
        'introduce yourself',
        'tu kaun hai', 'tum kaun ho', 'aap kaun', 'tera naam kya',
        'tumhara naam', 'apka naam', 'kaun ho tum',
        'tumi ke', 'tui ke', 'apni ke', 'tomar naam ki', 'ki naam tomar',
        'ke tumi', 'নাম কি', 'তুমি কে', 'आप कौन', 'तुम कौन', 'तेरा नाम'
    ]
    for pattern in identity_patterns:
        if pattern in q:
            return 'identity', q

    # Time
    time_patterns = [
        'what time', 'what is the time', 'current time', 'tell me the time',
        'time now', "what's the time", 'time please', 'kitna baj',
        'kya time', 'samay', 'time bata', 'samay kya', 'kya samay',
        'koyta baje', 'shomoy ki', 'ki shomoy'
    ]
    for pattern in time_patterns:
        if pattern in q:
            return 'time', q

    # Date
    date_patterns = [
        'what date', 'what is the date', 'current date', "today's date",
        'what day', 'aaj kya date', 'tarikh', 'aaj ki tarikh',
        'ajker tarikh', 'ki din'
    ]
    for pattern in date_patterns:
        if pattern in q:
            return 'date', q

    # YouTube
    if 'on youtube' in q or 'youtube pe' in q or 'youtube par' in q or 'youtube e' in q:
        return 'youtube', q
    if q.startswith('play ') or q.startswith('bajao '):
        return 'youtube', q

    # Quick message: "message maa I will be late"
    msg_patterns = [r'^message\s+(\S+)\s+(.+)', r'^msg\s+(\S+)\s+(.+)']
    for pattern in msg_patterns:
        match = re.match(pattern, q)
        if match:
            return 'quick_message', (match.group(1), match.group(2))

    # Search
    search_patterns = [
        'google search ', 'search for ', 'search karo ',
        'look up ', 'find out ', 'lookup ',
        'khojo ', 'dhundho ', 'search '
    ]
    for pattern in search_patterns:
        if q.startswith(pattern):
            term = q[len(pattern):].strip()
            return 'search', term

    # Open app/site
    open_patterns = ['open ', 'launch ', 'start ', 'kholo ', 'chalu kar ', 'kholun ']
    for pattern in open_patterns:
        if q.startswith(pattern):
            target = q.replace(pattern, '', 1).strip()
            return 'open', target

    # Website URL detection (must be a single word without spaces)
    if ' ' not in q and re.match(r'^[a-zA-Z0-9-]+\.(com|in|org|net|io|co|dev|me)$', q):
        return 'open', q

    # Messaging / Calls
    if 'send message' in q or 'phone call' in q or 'video call' in q:
        return 'communication', q

    # Fallback to AI
    return 'ai', q


# ==================== ACTION HANDLERS ====================

IDENTITY_RESPONSES = {
    'en': "I am JARVIS, created by Tushar. I'm his personal AI assistant. I help him execute tasks, answer questions, and manage his digital life intelligently.",
    'hi': "मैं जार्विस हूँ, मुझे तुषार ने बनाया है। मैं उनका पर्सनल AI असिस्टेंट हूँ। मैं उनके लिए काम करता हूँ और उनकी मदद करता हूँ।",
    'bn': "আমি জার্ভিস, আমাকে তুষার তৈরি করেছে। আমি তার পার্সোনাল AI অ্যাসিস্ট্যান্ট। আমি তার কাজে সাহায্য করি এবং তার ডিজিটাল জীবন পরিচালনা করি।",
}


def handleIdentity(lang='en'):
    response = IDENTITY_RESPONSES.get(lang, IDENTITY_RESPONSES['en'])
    speak(response, lang)


def handleTime(lang='en'):
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    if lang == 'hi':
        speak(f"Sir, अभी समय {time_str} है।", 'hi')
    elif lang == 'bn':
        speak(f"Sir, এখন সময় {time_str}।", 'bn')
    else:
        speak(f"Sir, the current time is {time_str}.", 'en')


def handleDate(lang='en'):
    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    if lang == 'hi':
        speak(f"Sir, आज की तारीख है {date_str}।", 'hi')
    elif lang == 'bn':
        speak(f"Sir, আজকের তারিখ হলো {date_str}।", 'bn')
    else:
        speak(f"Sir, today is {date_str}.", 'en')


def handleSearch(term):
    if not term:
        speak("What would you like me to search for, Sir?")
        return
    speak(f"Searching for {term}, Sir.")
    url = f"https://www.google.com/search?q={term.replace(' ', '+')}"
    webbrowser.open(url)


def handleOpen(target):
    from engine.features import openCommand
    openCommand("open " + target)


def handleYoutube(query):
    from engine.features import PlayYoutube
    PlayYoutube(query)


def handleQuickMessage(contact_name, message_text):
    from engine.features import findContact, whatsApp
    speak(f"Sending message to {contact_name}")
    contact_no, name = findContact(f"send message to {contact_name}")
    if contact_no != 0:
        whatsApp(contact_no, message_text, 'message', name)
    else:
        speak(f"Sorry Sir, I couldn't find {contact_name} in your contacts.")


def handleCommunication(query):
    from engine.features import findContact, whatsApp, makeCall, sendMessage
    contact_no, name = findContact(query)
    if contact_no != 0:
        speak("Which mode you want to use Sir, WhatsApp or mobile?")
        preference = takecommand()
        print(preference)

        if not preference:
            speak("I didn't get a response, Sir. Please try again.")
            return

        if "mobile" in preference:
            if "send message" in query or "send sms" in query:
                speak("What message should I send, Sir?")
                msg_text = takecommand()
                if not msg_text:
                    speak("I didn't catch the message, Sir. Please try again.")
                    return
                sendMessage(msg_text, contact_no, name)
            elif "phone call" in query:
                makeCall(name, contact_no)
            else:
                speak("I didn't catch that, Sir. Please try again.")
        elif "whatsapp" in preference:
            if "send message" in query:
                speak("What message should I send, Sir?")
                msg_text = takecommand()
                if not msg_text:
                    speak("I didn't catch the message, Sir. Please try again.")
                    return
                whatsApp(contact_no, msg_text, 'message', name)
            elif "phone call" in query:
                whatsApp(contact_no, '', 'call', name)
            else:
                whatsApp(contact_no, '', 'video call', name)
        else:
            speak("I didn't catch that, Sir. Please say WhatsApp or mobile.")


def handleAI(query, lang='en'):
    from engine.features import chatBot
    # Check if user wants response in a specific language
    target = detectTargetLanguage(query)
    if target:
        lang = target
    chatBot(query, lang)


# ==================== MAIN COMMAND PROCESSOR ====================
@eel.expose
def allCommands(message=1):
    if message == 1:
        query = takecommand()
        print(query)
        try:
            eel.senderText(query)
        except Exception:
            pass
    else:
        query = str(message).lower()
        try:
            eel.DisplayMessage(query)
        except Exception:
            pass
        try:
            eel.senderText(query)
        except Exception:
            pass

    if not query or query.strip() == "":
        try:
            eel.ShowHood()
        except Exception:
            pass
        return

    try:
        lang = detectLanguage(query)
        sub_commands = splitCompoundCommand(query)
        
        # Hybrid Decision: Identify if sub_commands are local actions or require AI
        tasks = []
        for cmd in sub_commands:
            intent, data = classifyIntent(cmd)
            tasks.append({'intent': intent, 'data': data, 'cmd': cmd})

        # Process each task
        for task in tasks:
            intent = task['intent']
            data = task['data']
            cmd = task['cmd']

            # ACTION SYSTEM: Local Tasks (No AI API)
            if intent != 'ai':
                # Generate Structured Action Response for logs/console
                action_plan = {
                    "type": "action",
                    "intent": intent,
                    "language": lang,
                    "actions": []
                }
                
                if intent == 'identity':
                    action_plan["actions"].append({"type": "respond", "content": "identity_info"})
                    handleIdentity(lang)
                elif intent == 'time':
                    action_plan["actions"].append({"type": "get_system_info", "target": "time"})
                    handleTime(lang)
                elif intent == 'date':
                    action_plan["actions"].append({"type": "get_system_info", "target": "date"})
                    handleDate(lang)
                elif intent == 'search':
                    action_plan["actions"].append({"type": "open_browser", "action": "google_search", "query": data})
                    handleSearch(data)
                elif intent == 'open':
                    action_plan["actions"].append({"type": "launch", "target": data})
                    handleOpen(data)
                elif intent == 'youtube':
                    action_plan["actions"].append({"type": "open_url", "target": "youtube", "query": data})
                    handleYoutube(data)
                elif intent == 'quick_message':
                    contact_name, msg_text = data
                    action_plan["actions"].append({"type": "messaging", "contact": contact_name, "message": msg_text})
                    handleQuickMessage(contact_name, msg_text)
                elif intent == 'communication':
                    action_plan["actions"].append({"type": "interactive_workflow", "task": "communication"})
                    handleCommunication(data)
                
                print(f"[JARVIS Action Plan]\n{json.dumps(action_plan, indent=2)}")

            # AI SYSTEM: General Knowledge / Conversation (Use API)
            else:
                print(f"[JARVIS Decision] AI API required for: '{cmd}'")
                handleAI(data, lang)

    except Exception as e:
        print("error: ", e)

    try:
        eel.ShowHood()
    except Exception:
        pass


# ==================== REAL-TIME SYSTEM STATS ====================
_disk_cache = {'data': {}, 'ts': 0}
_ip_cache = {'ip': '0.0.0.0', 'ts': 0}

@eel.expose
def getSystemStats():
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    now = time.time()
    # Disk: refresh every 30s
    if now - _disk_cache['ts'] > 30:
        disks = {}
        for p in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(p.mountpoint)
                disks[p.device.replace('\\', '')] = round(u.percent, 1)
            except Exception:
                pass
        _disk_cache['data'] = disks
        _disk_cache['ts'] = now
    disks = _disk_cache['data']
    # IP: refresh every 60s
    if now - _ip_cache['ts'] > 60:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            _ip_cache['ip'] = s.getsockname()[0]
            s.close()
        except Exception:
            _ip_cache['ip'] = '0.0.0.0'
        _ip_cache['ts'] = now
    net = psutil.net_io_counters()
    return {
        'cpu': cpu, 'ram': ram.percent,
        'ram_used': round(ram.used / (1024**3), 1),
        'ram_total': round(ram.total / (1024**3), 1),
        'disks': disks,
        'net_sent': round(net.bytes_sent / (1024**2), 1),
        'net_recv': round(net.bytes_recv / (1024**2), 1),
        'ip': _ip_cache['ip']
    }