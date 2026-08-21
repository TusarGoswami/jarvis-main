import pyttsx3
import eel
import time
import re
import os
from gtts import gTTS
import pygame
import tempfile
import edge_tts
import asyncio


# ==================== LANGUAGE DETECTION ====================
HINDI_WORDS = {
    'kya', 'hai', 'kaise', 'hain', 'mujhe', 'batao', 'bhai', 'yaar', 'aur',
    'karo', 'karke', 'bata', 'mera', 'tera', 'hum', 'tum', 'kuch', 'nahi',
    'acha', 'theek', 'kholo', 'band', 'sunao', 'dikhao', 'kab',
    'kahan', 'kisko', 'kitna', 'kyun', 'abhi', 'bahut', 'accha', 'suno',
    'bol', 'bolo', 'dekho', 'jao', 'padho', 'likho', 'samjho', 'socho',
    'chalo', 'wala', 'wali', 'raha', 'rahi', 'hoga', 'hogi', 'tha', 'thi',
    'par', 'lekin', 'phir', 'matlab', 'samay', 'din', 'raat', 'subah',
    'shaam', 'namaste', 'dhanyawaad', 'shukriya', 'maaf',
    'hal', 'ho'
}

BENGALI_WORDS = {
    'ki', 'kemon', 'acho', 'koro', 'bolo', 'amake', 'tumi', 'ami',
    'ache', 'holo', 'kore', 'dao', 'bol', 'dekho', 'jao', 'eso',
    'kothay', 'keno', 'kokhon', 'koto', 'bhalo', 'kharap', 'ebar',
    'ekhon', 'pore', 'age', 'dhonnobad', 'dada', 'didi', 'bhai',
    'ar', 'ba', 'ta', 'eta', 'oita', 'shob', 'kichu', 'nei',
    'hobe', 'korbo', 'jabo', 'khabo', 'dekhbo', 'bolbo', 'likhbo',
    'sunbo', 'amar', 'tomar', 'apnar', 'shomoy', 'aj', 'kal'
}


def detectLanguage(text):
    if not text:
        return 'en'

    # Check for Devanagari (Hindi) script
    if re.search(r'[\u0900-\u097F]', text):
        return 'hi'

    # Check for Bengali script
    if re.search(r'[\u0980-\u09FF]', text):
        return 'bn'

    # Romanized detection
    words = set(text.lower().split())
    hindi_score = len(words & HINDI_WORDS)
    bengali_score = len(words & BENGALI_WORDS)

    if hindi_score >= 2 and hindi_score >= bengali_score:
        return 'hi'
    if bengali_score >= 2 and bengali_score > hindi_score:
        return 'bn'

    return 'en'


def detectTargetLanguage(text):
    """Detect if the user is requesting a response in a specific language.
    E.g., 'tell me a poem in bengali' → 'bn', 'hindi mein batao' → 'hi'
    """
    q = text.lower()
    # Bengali target
    bn_patterns = ['in bengali', 'in bangla', 'bengali mein', 'bangla te', 'banglay']
    for p in bn_patterns:
        if p in q:
            return 'bn'
    # Hindi target
    hi_patterns = ['in hindi', 'hindi mein', 'hindi me', 'hindi mai']
    for p in hi_patterns:
        if p in q:
            return 'hi'
    # English target
    en_patterns = ['in english', 'english mein', 'english me']
    for p in en_patterns:
        if p in q:
            return 'en'
    return None


# ==================== SPEECH ENGINE ====================
pygame.mixer.init()

# Premium neural voices from Microsoft Edge TTS
EDGE_VOICES = {
    'en': 'en-US-AriaNeural',       # Natural, warm female voice
    'hi': 'hi-IN-SwaraNeural',      # Natural Hindi female voice
    'bn': 'bn-IN-TanishaaNeural',   # Natural Bengali female voice
}


async def _edge_tts_generate(text, voice, filepath):
    """Generate speech audio using Edge TTS neural voice."""
    communicate = edge_tts.Communicate(text, voice, rate='+8%', pitch='+5Hz')
    await communicate.save(filepath)


def _playAudioFile(filepath):
    """Play an audio file through pygame and clean up."""
    pygame.mixer.music.load(filepath)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    pygame.mixer.music.unload()
    try:
        os.remove(filepath)
    except Exception:
        pass


def _speakWithEdgeTTS(text, lang='en'):
    """Primary TTS: Microsoft Edge neural voices (best quality)."""
    try:
        voice = EDGE_VOICES.get(lang, EDGE_VOICES['en'])
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            filepath = f.name
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_edge_tts_generate(text, voice, filepath))
        finally:
            loop.close()
        _playAudioFile(filepath)
    except Exception as e:
        print(f"Edge TTS error: {e}, falling back to gTTS")
        _speakWithGTTS(text, lang)


def _speakWithGTTS(text, lang='en'):
    """Fallback TTS: Google Text-to-Speech."""
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            filepath = f.name
        tts.save(filepath)
        _playAudioFile(filepath)
    except Exception as e:
        print(f"gTTS error: {e}, falling back to pyttsx3")
        _speakWithPyttsx3(text, lang)


# Cached pyttsx3 engine — initialized once, reused across calls
_pyttsx3_engine = None

def _speakWithPyttsx3(text, lang='en'):
    """Last resort TTS: offline pyttsx3 (Windows SAPI5)."""
    global _pyttsx3_engine
    try:
        if _pyttsx3_engine is None:
            _pyttsx3_engine = pyttsx3.init('sapi5')
            _pyttsx3_engine.setProperty('rate', 174)
            _pyttsx3_engine.setProperty('volume', 1.0)
        _pyttsx3_engine.say(text)
        _pyttsx3_engine.runAndWait()
    except Exception as e:
        _pyttsx3_engine = None  # Reset so next call retries init
        print(f"pyttsx3 error: {e} — all TTS engines failed")


def speak(text, lang=None):
    text = str(text)
    if not text.strip():
        return

    if lang is None:
        lang = detectLanguage(text)

    try:
        eel.DisplayMessage(text)
    except Exception:
        pass
    try:
        eel.receiverText(text)
    except Exception:
        pass

    # Use Edge TTS neural voices (premium quality), with gTTS and pyttsx3 as fallbacks
    _speakWithEdgeTTS(text, lang if lang in ('hi', 'bn', 'en') else 'en')
