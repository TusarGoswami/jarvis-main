import os
import time
import base64
import logging
import warnings
from typing import Optional, Tuple, Any, List, Dict
from google import genai
from google.genai import types
from groq import Groq

from app.config import settings
from app.core.sanitizer import sanitize_text

# Suppress SDK deprecation / AFC notices from Google GenAI
warnings.filterwarnings("ignore", message=".*automatic function calling.*")

logger = logging.getLogger("vocalis.llm_provider")

class CircuitBreaker:
    """
    Lightweight circuit breaker for LLM providers.
    Prevents calling an unresponsive/exhausted provider and skips directly to fallback.
    """
    def __init__(self, name: str, failure_threshold: int = 3, cooldown_seconds: float = 30.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.consecutive_failures = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_attempt(self) -> bool:
        if self.state == "CLOSED":
            return True
        now = time.time()
        if self.state == "OPEN":
            if now - self.last_failure_time > self.cooldown_seconds:
                logger.info(f"[CircuitBreaker] {self.name} cooldown elapsed. Switching to HALF_OPEN to test recovery.")
                self.state = "HALF_OPEN"
                return True
            return False
        return True  # HALF_OPEN

    def record_success(self):
        if self.state != "CLOSED":
            logger.info(f"[CircuitBreaker] {self.name} call succeeded. Resetting state to CLOSED.")
        self.consecutive_failures = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        if self.consecutive_failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                f"[CircuitBreaker] {self.name} reached {self.consecutive_failures} consecutive failures. "
                f"Circuit tripped to OPEN for {self.cooldown_seconds}s. Subsequent calls will skip straight to fallback."
            )

gemini_circuit_breaker = CircuitBreaker("Gemini", failure_threshold=3, cooldown_seconds=30.0)
groq_circuit_breaker = CircuitBreaker("Groq", failure_threshold=3, cooldown_seconds=30.0)

_current_gemini_key_index: int = 0
_gemini_clients: dict[str, genai.Client] = {}
_groq_client: Optional[Groq] = None

def _mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "******"
    return f"{key[:4]}...****"

def get_gemini_client(force_next: bool = False) -> Tuple[Optional[genai.Client], str]:
    """
    Returns active Gemini client and masked key, supporting round-robin failover across multiple keys.
    """
    global _current_gemini_key_index, _gemini_clients
    keys = settings.GEMINI_API_KEYS
    if not keys:
        return None, "none"

    if force_next:
        _current_gemini_key_index = (_current_gemini_key_index + 1) % len(keys)
        logger.info(f"Switched active Gemini API Key to slot #{_current_gemini_key_index + 1} ({_mask_key(keys[_current_gemini_key_index])})")

    _current_gemini_key_index = _current_gemini_key_index % len(keys)
    active_key = keys[_current_gemini_key_index]

    if active_key not in _gemini_clients:
        try:
            _gemini_clients[active_key] = genai.Client(api_key=active_key)
        except Exception as e:
            sanitized_err = sanitize_text(str(e))
            logger.error(f"Failed to initialize Gemini Client for key slot #{_current_gemini_key_index + 1}: {sanitized_err}")
            return None, active_key

    return _gemini_clients[active_key], active_key

def get_groq_client() -> Optional[Groq]:
    global _groq_client
    if _groq_client is None and settings.GROQ_API_KEY:
        try:
            _groq_client = Groq(api_key=settings.GROQ_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Groq Client: {sanitize_text(str(e))}")
    return _groq_client

def generate_gemini_content_sync(
    contents: Any,
    config: Optional[types.GenerateContentConfig] = None,
    model: Optional[str] = None,
    max_retries_per_key: int = 2
) -> Any:
    """
    Synchronous content generation with automatic multi-key failover and exponential backoff retry for transient errors.
    """
    if not gemini_circuit_breaker.can_attempt():
        raise RuntimeError("Gemini circuit breaker is OPEN. Skipping Gemini call.")

    keys = settings.GEMINI_API_KEYS
    target_model = model or settings.GEMINI_MODEL
    
    if not keys:
        raise ValueError("No Gemini API keys configured.")

    total_keys = len(keys)
    attempts = 0
    last_exception = None

    while attempts < total_keys:
        client, active_key = get_gemini_client(force_next=(attempts > 0))
        if client:
            # Retry loop with exponential backoff on transient errors
            for retry_idx in range(max_retries_per_key):
                try:
                    response = client.models.generate_content(
                        model=target_model,
                        contents=contents,
                        config=config
                    )
                    gemini_circuit_breaker.record_success()
                    return response
                except Exception as e:
                    sanitized_err = sanitize_text(str(e))
                    err_str = sanitized_err.lower()
                    last_exception = RuntimeError(sanitized_err)
                    is_transient = any(term in err_str for term in ["429", "timeout", "timed out", "rate_limit", "resource_exhausted", "service_unavailable", "503"])

                    if is_transient and retry_idx < (max_retries_per_key - 1):
                        backoff = 0.5 * (2 ** retry_idx)
                        logger.warning(f"[Retry] Transient error on key slot #{_current_gemini_key_index + 1}. Retrying in {backoff}s ({sanitized_err})...")
                        time.sleep(backoff)
                        continue
                    else:
                        is_quota_or_auth = any(term in err_str for term in ["429", "resource_exhausted", "quota", "rate_limit", "unauthenticated", "invalid_argument", "permission_denied"])
                        if is_quota_or_auth and total_keys > 1:
                            logger.warning(
                                f"[Multi-Key Failover] Gemini Key slot #{_current_gemini_key_index + 1} ({_mask_key(active_key)}) encountered error: {sanitized_err}. "
                                f"Failing over to next API key..."
                            )
                        else:
                            logger.warning(f"Gemini call error on key slot #{_current_gemini_key_index + 1}: {sanitized_err}")
                        break
        
        attempts += 1

    gemini_circuit_breaker.record_failure()
    raise last_exception or RuntimeError("All Gemini API keys failed or were exhausted.")

async def generate_multimodal_content(
    prompt_text: str,
    image_bytes: Optional[bytes] = None,
    system_instruction: Optional[str] = None
) -> Tuple[str, str]:
    """
    Generates content using Gemini with automatic multi-key failover and circuit breaker protection,
    falling back to Groq if Gemini is unavailable or circuit-broken.
    """
    import asyncio
    loop = asyncio.get_event_loop()

    contents = []
    if image_bytes:
        contents.append(
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        )
    contents.append(prompt_text)

    config_args = {}
    if system_instruction:
        config_args["system_instruction"] = system_instruction
    cfg = types.GenerateContentConfig(**config_args) if config_args else None

    # 1. Try Gemini if circuit allows
    if gemini_circuit_breaker.can_attempt():
        try:
            def _call_gemini():
                return generate_gemini_content_sync(contents=contents, config=cfg, model=settings.GEMINI_MODEL)

            resp = await loop.run_in_executor(None, _call_gemini)
            if resp.text:
                return resp.text, f"gemini ({settings.GEMINI_MODEL}, slot #{_current_gemini_key_index + 1})"
        except Exception as e:
            logger.warning(f"Gemini attempt failed ({sanitize_text(str(e))}). Checking fallback model...")
            
            # Try fallback model
            try:
                def _call_fallback():
                    return generate_gemini_content_sync(contents=contents, config=cfg, model=settings.FALLBACK_MODEL)
                resp = await loop.run_in_executor(None, _call_fallback)
                if resp.text:
                    return resp.text, f"gemini ({settings.FALLBACK_MODEL}, slot #{_current_gemini_key_index + 1})"
            except Exception as fe:
                logger.error(f"Gemini fallback model also failed: {sanitize_text(str(fe))}")
    else:
        logger.info("[CircuitBreaker] Gemini circuit breaker is OPEN. Skipping straight to Groq fallback.")

    # 2. Try Groq (Fallback) if Groq circuit allows
    if groq_circuit_breaker.can_attempt():
        groq_client = get_groq_client()
        if groq_client:
            try:
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})

                if image_bytes:
                    b64_image = base64.b64encode(image_bytes).decode("utf-8")
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}
                            }
                        ]
                    })
                    groq_model = settings.GROQ_VISION_MODEL
                else:
                    messages.append({"role": "user", "content": prompt_text})
                    groq_model = settings.GROQ_MODEL

                def _call_groq():
                    return groq_client.chat.completions.create(
                        model=groq_model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1024
                    )

                chat_completion = await loop.run_in_executor(None, _call_groq)
                text = chat_completion.choices[0].message.content
                groq_circuit_breaker.record_success()
                return text, f"groq ({groq_model})"
            except Exception as ge:
                groq_circuit_breaker.record_failure()
                logger.error(f"Groq fallback failed: {sanitize_text(str(ge))}")

    return "Api has been exhausted, plz try after sometime", "exhausted"

