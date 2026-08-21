import asyncio
import io
import os
import re
import tempfile
import time
import edge_tts
import pyttsx3
import speech_recognition as sr

HINDI_WORDS = {
    'kya', 'hai', 'kaise', 'hain', 'mujhe', 'batao', 'bhai', 'yaar', 'aur',
    'karo', 'karke', 'bata', 'mera', 'tera', 'hum', 'tum', 'kuch', 'nahi',
    'acha', 'theek', 'kholo', 'band', 'sunao', 'dikhao', 'kab',
    'kahan', 'kisko', 'kitna', 'kyun', 'abhi', 'bahut', 'accha', 'suno',
    'bol', 'bolo', 'dekho', 'jao', 'padho', 'likho', 'samjho', 'socho',
    'chalo', 'wala', 'wali', 'raha', 'rahi', 'hoga', 'hogi', 'tha', 'thi',
    'par', 'lekin', 'phir', 'matlab', 'samay', 'din', 'raat', 'subah',
    'shaam', 'namaste', 'dhanyawaad', 'shukriya', 'maaf', 'hal', 'ho'
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

EDGE_VOICES = {
    'en': 'en-US-AriaNeural',
    'hi': 'hi-IN-SwaraNeural',
    'bn': 'bn-IN-TanishaaNeural',
}

def detect_language(text: str) -> str:
    if not text:
        return 'en'
    if re.search(r'[\u0900-\u097F]', text):
        return 'hi'
    if re.search(r'[\u0980-\u09FF]', text):
        return 'bn'

    words = set(re.findall(r'\w+', text.lower()))
    hindi_score = len(words & HINDI_WORDS)
    bengali_score = len(words & BENGALI_WORDS)

    if hindi_score >= 2 and hindi_score >= bengali_score:
        return 'hi'
    if bengali_score >= 2 and bengali_score > hindi_score:
        return 'bn'
    return 'en'

def detect_target_language(text: str) -> str | None:
    q = text.lower()
    for p in ['in bengali', 'in bangla', 'bengali mein', 'bangla te', 'banglay']:
        if p in q:
            return 'bn'
    for p in ['in hindi', 'hindi mein', 'hindi me', 'hindi mai']:
        if p in q:
            return 'hi'
    for p in ['in english', 'english mein', 'english me']:
        if p in q:
            return 'en'
    return None

async def synthesize_speech_bytes(text: str, lang: str = 'en') -> bytes:
    """Synthesizes text into MP3 bytes using Edge TTS neural voices."""
    voice = EDGE_VOICES.get(lang, EDGE_VOICES['en'])
    communicate = edge_tts.Communicate(text, voice, rate='+8%', pitch='+5Hz')
    buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])
    return buffer.getvalue()

def recognize_speech_from_mic(timeout: int = 5) -> dict:
    """Capture mic input and recognize speech with English/Hindi fallback."""
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            r.pause_threshold = 0.8
            r.adjust_for_ambient_noise(source, duration=0.6)
            audio = r.listen(source, timeout=timeout, phrase_time_limit=8)

        try:
            query = r.recognize_google(audio, language='en-IN')
            lang = detect_language(query)
            return {"status": "success", "transcript": query, "language": lang}
        except sr.UnknownValueError:
            try:
                query = r.recognize_google(audio, language='hi-IN')
                return {"status": "success", "transcript": query, "language": "hi"}
            except sr.UnknownValueError:
                return {"status": "error", "message": "Speech could not be understood"}
    except sr.WaitTimeoutError:
        return {"status": "timeout", "message": "Listening timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
