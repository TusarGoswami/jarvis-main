import io
import mss
from PIL import Image
import base64

def capture_screen_bytes(max_dim: int = 1280, quality: int = 75) -> bytes:
    """Captures the primary screen monitor and returns JPEG compressed bytes."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        
        # Resize while maintaining aspect ratio
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue()

def capture_screen_base64() -> str:
    """Returns base64 encoded screen image string."""
    raw_bytes = capture_screen_bytes()
    return base64.b64encode(raw_bytes).decode('utf-8')

def decode_image_bytes(image_data: str | bytes) -> bytes:
    if isinstance(image_data, bytes):
        return image_data
    if image_data.startswith("data:image"):
        image_data = image_data.split(",", 1)[1]
    return base64.b64decode(image_data)
