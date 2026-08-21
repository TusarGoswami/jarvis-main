from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Optional
from app.core.agent import process_turn
from app.core.multimodal import capture_screen_bytes, decode_image_bytes
from app.core.speech_service import synthesize_speech_bytes

router = APIRouter()

class CommandRequest(BaseModel):
    query: str
    image_base64: Optional[str] = None
    language: Optional[str] = None
    allow_actions: bool = True

class TTSRequest(BaseModel):
    text: str
    language: str = "en"

@router.post("/command")
async def execute_command(req: CommandRequest):
    image_bytes = None
    if req.image_base64:
        try:
            image_bytes = decode_image_bytes(req.image_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image format: {e}")
            
    response = await process_turn(
        user_query=req.query,
        image_bytes=image_bytes,
        client_lang=req.language,
        allow_actions=req.allow_actions
    )
    return response.model_dump()

@router.post("/analyze-screen")
async def analyze_screen_endpoint(query: str = "Explain what is on the screen and what actions I should take."):
    screen_bytes = capture_screen_bytes()
    response = await process_turn(
        user_query=query,
        image_bytes=screen_bytes,
        allow_actions=False
    )
    return response.model_dump()

@router.post("/tts")
async def text_to_speech(req: TTSRequest):
    try:
        audio_bytes = await synthesize_speech_bytes(req.text, req.language)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {e}")
