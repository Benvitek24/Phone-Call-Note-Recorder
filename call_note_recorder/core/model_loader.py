"""Loads Whisper (GPU) and the LLM (CPU) once at startup, off the UI thread.

Emits models_ready(whisper, llm). If the model file is missing the app must
keep running without summarization (spec error rule), so we still emit Whisper
with llm=None and report the problem via model_missing.
"""

import os

from PyQt6.QtCore import QThread, pyqtSignal

from utils.paths import MODEL_FILE
from utils.logger import get_logger

log = get_logger("loader")


class ModelLoaderThread(QThread):
    progress      = pyqtSignal(str)
    models_ready  = pyqtSignal(object, object)  # whisper_model, llm (llm may be None)
    model_missing = pyqtSignal()
    error_signal  = pyqtSignal(str)

    def run(self):
        whisper_model = None
        llm = None
        try:
            self.progress.emit("Loading transcription model...")
            from faster_whisper import WhisperModel
            # Offline-first: load from the local cache without contacting
            # HuggingFace (faster startup, works behind Zscaler / offline). Only
            # if it isn't cached yet (first run) do we download it once.
            try:
                whisper_model = WhisperModel(
                    "small", device="cuda", compute_type="float16",
                    local_files_only=True,
                )
                log.info("Whisper loaded from local cache (small, cuda, float16)")
            except Exception:  # noqa: BLE001 - not cached yet -> download once
                log.info("Whisper model not cached — downloading once from HuggingFace")
                self.progress.emit("Downloading transcription model (first run)...")
                whisper_model = WhisperModel(
                    "small", device="cuda", compute_type="float16",
                )
                log.info("Whisper downloaded + loaded (small, cuda, float16)")
        except Exception as e:  # noqa: BLE001
            log.exception("Whisper load failed")
            self.error_signal.emit(f"Transcription model failed to load: {e}")
            return

        try:
            if not os.path.exists(MODEL_FILE):
                log.error("LLM model file missing: %s", MODEL_FILE)
                self.model_missing.emit()
            else:
                self.progress.emit("Loading note-writing model...")
                from core.llm_engine import load_llm
                llm = load_llm()
                log.info("LLM loaded (CPU)")
        except Exception as e:  # noqa: BLE001
            log.exception("LLM load failed")
            # Non-fatal: app can still transcribe.
            self.error_signal.emit(f"Note model failed to load: {e}")

        self.models_ready.emit(whisper_model, llm)
