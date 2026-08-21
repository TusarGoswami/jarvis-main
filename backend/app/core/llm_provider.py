import os
import base64
import logging
from typing import Optional, Tuple
from google import genai
from google.genai import types
from groq import Groq

from app.config import settings

logger = logging.getLogger("vocalis.llm_provider")

_gemini_client = None
_groq_client = None

def get_gemini_client() -> Optional[genai.Client]:
    global _gemini_client
    if _gemini_client is None and settings.GEMINI_API_KEY:
        try:
            _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
    return _gemini_client

def get_groq_client() -> Optional[Groq]:
    global _groq_client
    if _groq_client is None and settings.GROQ_API_KEY:
        try:
            _groq_client = Groq(api_key=settings.GROQ_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Groq Client: {e}")
    return _groq_client

async def generate_multimodal_content(
    prompt_text: str,
    image_bytes: Optional[bytes] = None,
    system_instruction: Optional[str] = None
) -> Tuple[str, str]:
    """
    Generates content using Gemini, falling back to Groq if Gemini fails or is exhausted.
    Returns:
        Tuple[response_text, provider_name]
    """
    # 1. Try Gemini (Primary)
    gemini_client = get_gemini_client()
    if gemini_client:
        try:
            contents = []
            if image_bytes:
                contents.append(
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                )
            contents.append(prompt_text)

            config = {}
            if system_instruction:
                config["system_instruction"] = system_instruction

            # Run in threadpool since genai.Client is synchronous
            import asyncio
            loop = asyncio.get_event_loop()
            
            def _call_gemini():
                return gemini_client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(**config) if config else None
                )

            resp = await loop.run_in_executor(None, _call_gemini)
            if resp.text:
                return resp.text, f"gemini ({settings.GEMINI_MODEL})"
        except Exception as e:
            logger.warning(f"Gemini generation failed, trying fallback model or Groq. Error: {e}")
            
            # Try fallback model on Gemini (e.g. 1.5-flash) before completely shifting to Groq
            try:
                def _call_gemini_fallback():
                    return gemini_client.models.generate_content(
                        model=settings.FALLBACK_MODEL,
                        contents=contents,
                        config=types.GenerateContentConfig(**config) if config else None
                    )
                resp = await loop.run_in_executor(None, _call_gemini_fallback)
                if resp.text:
                    return resp.text, f"gemini ({settings.FALLBACK_MODEL})"
            except Exception as fe:
                logger.error(f"Gemini fallback model also failed: {fe}")

    # 2. Try Groq (Fallback)
    groq_client = get_groq_client()
    if groq_client:
        try:
            import asyncio
            loop = asyncio.get_event_loop()

            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})

            if image_bytes:
                # Vision query on Groq
                base64_image = base64.b64encode(image_bytes).decode("utf-8")
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                })
                model_to_use = settings.GROQ_VISION_MODEL
            else:
                # Text query on Groq
                messages.append({"role": "user", "content": prompt_text})
                model_to_use = settings.GROQ_MODEL

            def _call_groq():
                return groq_client.chat.completions.create(
                    model=model_to_use,
                    messages=messages
                )

            chat_completion = await loop.run_in_executor(None, _call_groq)
            output_text = chat_completion.choices[0].message.content
            if output_text:
                return output_text, f"groq ({model_to_use})"
        except Exception as e:
            logger.error(f"Groq fallback generation failed: {e}")
            raise RuntimeError(f"Both Gemini and Groq API keys are exhausted or failed. Last error: {e}")

    raise RuntimeError("No configured API keys (Gemini or Groq) found or loaded.")
