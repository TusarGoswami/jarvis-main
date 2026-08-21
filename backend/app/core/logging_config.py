import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from app.core.sanitizer import sanitize_text

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(_BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "vocalis.log")

class StructuredJsonFormatter(logging.Formatter):
    """
    Formats log records as structured JSON, automatically sanitizing sensitive data.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize_text(record.getMessage())
        }

        # Include custom extra metadata if present
        if hasattr(record, "session_id"):
            log_obj["session_id"] = getattr(record, "session_id")
        if hasattr(record, "task_id"):
            log_obj["task_id"] = getattr(record, "task_id")
        if hasattr(record, "step"):
            log_obj["step"] = getattr(record, "step")
        if hasattr(record, "latency_ms"):
            log_obj["latency_ms"] = getattr(record, "latency_ms")
        if hasattr(record, "provider"):
            log_obj["provider"] = getattr(record, "provider")
        if hasattr(record, "phase"):
            log_obj["phase"] = getattr(record, "phase")

        if record.exc_info:
            log_obj["exception"] = sanitize_text(self.formatException(record.exc_info))

        return json.dumps(log_obj)

def setup_logging():
    """Configures console and rotating structured JSON file logging for the application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid duplicate handlers on reload
    if any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        return

    # Rotating File Handler (Max 10MB, up to 5 backup files)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(file_handler)

    # Console Handler (Human-readable for dev console)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

# Initialize logging on import
setup_logging()
