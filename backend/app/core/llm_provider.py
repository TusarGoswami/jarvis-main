import os
import base64
import logging
from typing import Optional, Tuple, Any, List
from google import genai
from google.genai import types
from groq import Groq

from app.config import settings

logger = logging.getLogger("vocalis.llm_provider")

_current_gemini_key_index: int = 0
_gemini_clients: dict[str, genai.Client] = {}
_groq_client: Optional[Groq] = None

def _mask_key(key: str) -> str:
    if not key or len(key) < 10:
        return "******"
    return f"{key[:6]}...{key[-4:]}"

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
            logger.error(f"Failed to initialize Gemini Client for key slot #{_current_gemini_key_index + 1}: {e}")
            return None, active_key

    return _gemini_clients[active_key], active_key

def get_groq_client() -> Optional[Groq]:
    global _groq_client
    if _groq_client is None and settings.GROQ_API_KEY:
        try:
            _groq_client = Groq(api_key=settings.GROQ_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Groq Client: {e}")
    return _groq_client

def generate_gemini_content_sync(
    contents: Any,
    config: Optional[types.GenerateContentConfig] = None,
    model: Optional[str] = None
) -> Any:
    """
    Synchronous content generation with automatic multi-key failover.
    Iterates across all configured GEMINI_API_KEYS if quota (429) or rate limits occur.
    """
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
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=config
                )
                return response
            except Exception as e:
                err_str = str(e).lower()
                last_exception = e
                is_quota_or_auth = any(term in err_str for term in ["429", "resource_exhausted", "quota", "rate_limit", "unauthenticated", "invalid_argument", "permission_denied"])
                
                if is_quota_or_auth and total_keys > 1:
                    logger.warning(
                        f"[Multi-Key Failover] Gemini Key slot #{_current_gemini_key_index + 1} ({_mask_key(active_key)}) encountered error: {e}. "
                        f"Automatically failing over to next API key..."
                    )
                else:
                    logger.warning(f"Gemini call error on key slot #{_current_gemini_key_index + 1}: {e}")
        
        attempts += 1

    # If all keys failed, raise last exception
    raise last_exception or RuntimeError("All Gemini API keys failed or were exhausted.")

async def generate_multimodal_content(
    prompt_text: str,
    image_bytes: Optional[bytes] = None,
    system_instruction: Optional[str] = None
) -> Tuple[str, str]:
    """
    Generates content using Gemini with automatic multi-key failover, falling back to Groq if all Gemini keys fail.
    Returns:
        Tuple[response_text, provider_name]
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

    # 1. Try Gemini with automatic multi-key failover
    try:
        def _call_gemini():
            return generate_gemini_content_sync(contents=contents, config=cfg, model=settings.GEMINI_MODEL)

        resp = await loop.run_in_executor(None, _call_gemini)
        if resp.text:
            return resp.text, f"gemini ({settings.GEMINI_MODEL}, slot #{_current_gemini_key_index + 1})"
    except Exception as e:
        logger.warning(f"All primary Gemini keys failed ({e}). Trying fallback model on Gemini...")
        
        # Try fallback model (e.g. gemini-1.5-flash) across keys
        try:
            def _call_fallback():
                return generate_gemini_content_sync(contents=contents, config=cfg, model=settings.FALLBACK_MODEL)
            resp = await loop.run_in_executor(None, _call_fallback)
            if resp.text:
                return resp.text, f"gemini ({settings.FALLBACK_MODEL}, slot #{_current_gemini_key_index + 1})"
        except Exception as fe:
            logger.error(f"Gemini fallback model also failed across all keys: {fe}")

    # 2. Try Groq (Fallback)
    groq_client = get_groq_client()
    if groq_client:
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})

            if image_bytes:
                # Groq vision model
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
            return text, f"groq ({groq_model})"
        except Exception as ge:
            logger.error(f"Groq fallback failed: {ge}")

    return "I am currently unable to process your request due to upstream AI provider unavailability.", "offline"
