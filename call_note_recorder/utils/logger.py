"""Rotating-file logging setup. Logs to %APPDATA%\\CallNoteRecorder\\logs\\app.log
and also echoes to the console during development.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from utils.paths import LOGS_DIR

_CONFIGURED = False


def setup_logging():
    """Configure root logging once. Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return logging.getLogger("call_note_recorder")

    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = os.path.join(LOGS_DIR, 'app.log')

    handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8'
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s: %(message)s'
    ))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    # Console handler only if there's a console (a no-window launch via pythonw
    # sets sys.stderr to None, which would otherwise crash logging).
    if sys.stderr is not None:
        root.addHandler(logging.StreamHandler())

    # Quiet chatty third-party libraries so our own State/flow logs stand out.
    for noisy in ("httpx", "httpcore", "huggingface_hub", "urllib3", "faster_whisper"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True
    return logging.getLogger("call_note_recorder")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"call_note_recorder.{name}")
