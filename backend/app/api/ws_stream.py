import json
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.agent import process_turn
from app.core.multimodal import capture_screen_bytes, decode_image_bytes
from app.core.speech_service import synthesize_speech_bytes
from app.core.tools import get_system_stats

router = APIRouter()

@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        # Send initial connection handshake and system stats
        await websocket.send_json({
            "type": "handshake",
            "status": "connected",
            "stats": get_system_stats()
        })

        while True:
            raw_text = await websocket.receive_text()
            data = json.loads(raw_text)
            msg_type = data.get("type", "query")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "stats": get_system_stats()})
                continue

            if msg_type == "query":
                query_text = data.get("query", "")
                attach_screen = data.get("include_screen", False)
                custom_image = data.get("image_base64")
                lang = data.get("language")
                turn_id = data.get("turn_id")
                max_tokens = data.get("max_tokens")

                image_bytes = None
                if custom_image:
                    image_bytes = decode_image_bytes(custom_image)
                elif attach_screen:
                    image_bytes = capture_screen_bytes()

                # Send processing indicator
                await websocket.send_json({"type": "status", "state": "processing", "turn_id": turn_id})

                # Define intermediate step progress streaming callback
                async def stream_step(step_record: dict):
                    try:
                        await websocket.send_json({
                            "type": "step_update",
                            "turn_id": turn_id,
                            "step": step_record
                        })
                    except Exception:
                        pass

                # Execute multimodal turn
                response = await process_turn(
                    user_query=query_text,
                    image_bytes=image_bytes,
                    client_lang=lang,
                    max_tokens=max_tokens,
                    on_step_update=stream_step
                )

                # Optional: generate TTS audio in real-time
                audio_base64 = None
                try:
                    audio_bytes = await synthesize_speech_bytes(response.reply_text, response.language)
                    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                except Exception:
                    pass

                await websocket.send_json({
                    "type": "turn_result",
                    "turn_id": turn_id,
                    "data": response.model_dump(),
                    "audio_base64": audio_base64
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            from app.core.sanitizer import sanitize_text
            await websocket.send_json({"type": "error", "message": sanitize_text(str(e))})
        except Exception:
            pass

