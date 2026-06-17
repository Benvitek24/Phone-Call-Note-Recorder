"""Application controller: owns the icon + panel, runs the state machine, and
wires every QThread signal to the UI. Nothing here touches the UI from a worker
thread — all cross-thread communication is via signals.
"""

import time
import webbrowser

import pyperclip
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QMessageBox

from app.icon_widget import IconWidget
from app.panel_widget import PanelWidget
from core import audio_recorder
from core.audio_recorder import RecordingThread, detect_devices
from core.transcription import TranscriptionThread
from core.llm_engine import SummarizationThread
from core.model_loader import ModelLoaderThread
from core.update_checker import UpdateCheckThread
from version import GITHUB_REPO
from utils.logger import get_logger

log = get_logger("controller")

# States
IDLE, RECORDING, TRANSCRIBING, SUMMARIZING, COMPLETE = (
    "IDLE", "RECORDING", "TRANSCRIBING", "SUMMARIZING", "COMPLETE"
)

ONE_HOUR = 3600
TWO_HOURS = 7200


class AppController(QObject):
    def __init__(self, config_store, training_store):
        super().__init__()
        self.config = config_store
        self.training = training_store

        self.icon = IconWidget()
        self.panel = PanelWidget()
        self.tray = None  # set by main.py

        self.whisper_model = None
        self.llm = None
        self.models_loaded = False

        self.mic_device = None
        self.loopback_device = None
        self.has_loopback = False

        self.state = IDLE
        self._record_start = None
        self._one_hour_warned = False
        self._last_saved_note = None  # dedupe: text of the last training example saved this session
        self._last_transcript = ""

        # threads
        self.model_loader = None
        self.update_thread = None
        self.recording_thread = None
        self.transcription_thread = None
        self.summarization_thread = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._wire_signals()

    # --------------------------------------------------------------- startup
    def start(self):
        self.icon.show()
        self.panel.apply_saved_geometry(self.config.get_window_geometry())

        self.model_loader = ModelLoaderThread()
        self.model_loader.progress.connect(self._on_loader_progress)
        self.model_loader.models_ready.connect(self.on_models_ready)
        self.model_loader.model_missing.connect(self.on_model_missing)
        self.model_loader.error_signal.connect(self.on_loader_error)
        self.model_loader.start()

        self.update_thread = UpdateCheckThread()
        self.update_thread.update_available.connect(self.on_update_available)
        self.update_thread.start()

    def _wire_signals(self):
        # Icon
        self.icon.clicked.connect(self.on_record_pressed)
        # Panel top bar
        self.panel.record_clicked.connect(self.on_record_pressed)
        self.panel.delete_clicked.connect(self.on_delete)
        self.panel.minimize_clicked.connect(self.on_minimize)
        self.panel.close_clicked.connect(self.on_close_requested)
        # Panel column actions
        self.panel.copy_transcript.connect(
            lambda: self._copy(self.panel.get_transcript_text()))
        self.panel.copy_summary.connect(
            lambda: self._copy(self.panel.get_summary_text()))
        self.panel.copy_notes.connect(
            lambda: self._copy(self.panel.get_notes_text()))
        self.panel.save_clicked.connect(self.on_save_notes)
        self.panel.retry_clicked.connect(self.on_retry)
        self.panel.download_update_clicked.connect(self.on_download_update)
        # Geometry persistence
        self.panel.geometry_changed.connect(self._save_geometry)

    # ----------------------------------------------------------- model load
    def _on_loader_progress(self, msg):
        self.icon.set_loading_tooltip(msg)
        self.panel.set_status(msg, "loading")

    def on_models_ready(self, whisper_model, llm):
        self.whisper_model = whisper_model
        self.llm = llm
        self.models_loaded = whisper_model is not None
        if self.models_loaded:
            self.icon.set_ready()
            self.panel.set_status("Ready", "ready")
        log.info("Models ready (whisper=%s, llm=%s)",
                 whisper_model is not None, llm is not None)

    def on_model_missing(self):
        QMessageBox.warning(
            self.panel, "Model not found",
            "AI model file not found. Please reinstall the application.\n\n"
            "Recording and transcription will still work, but automatic notes "
            "are disabled."
        )

    def on_loader_error(self, msg):
        self.panel.set_status(f"Error: {msg}", "error")
        self.icon.set_loading_tooltip(f"Error: {msg}")

    # ------------------------------------------------------------- recording
    def on_record_pressed(self):
        if not self.models_loaded:
            return
        if self.state == IDLE:
            self.start_recording()
        elif self.state == RECORDING:
            self.stop_recording()
        elif self.state == COMPLETE:
            # Auto-clear current session, then immediately start a new recording.
            self._autosave_unsaved_notes()
            self._clear_session()
            self.start_recording()
        # TRANSCRIBING / SUMMARIZING: ignore record presses.

    def start_recording(self):
        self.mic_device, self.loopback_device = detect_devices()
        if self.mic_device is None:
            self.panel.set_status(
                "No microphone detected. Check audio settings.", "error")
            self._show_panel()
            return

        self.has_loopback = self.loopback_device is not None
        if self.has_loopback:
            self.panel.hide_loopback_warning()
        else:
            self.panel.show_loopback_warning()

        self._last_saved_note = None
        self._one_hour_warned = False
        self.panel.clear_all_content()
        self.panel.set_delete_visible(False)

        self.recording_thread = RecordingThread(self.mic_device, self.loopback_device)
        self.recording_thread.stopped_signal.connect(self.on_recording_stopped)
        self.recording_thread.error_signal.connect(self.on_recording_error)
        self.recording_thread.no_audio_signal.connect(self.on_no_audio)
        self.recording_thread.disconnect_signal.connect(self.on_disconnect)

        self._set_state(RECORDING)
        self._start_timer()
        self.recording_thread.start()

    def stop_recording(self):
        log.info("Stop pressed — signalling recording thread")
        self._stop_timer()
        if self.recording_thread and self.recording_thread.isRunning():
            self.panel.set_status("Saving audio...", "transcribing")
            self.recording_thread.stop()

    def on_recording_stopped(self, has_loopback):
        self.has_loopback = has_loopback
        self._set_state(TRANSCRIBING)
        self._show_panel()
        self._start_transcription()

    def on_recording_error(self, msg):
        self._stop_timer()
        self.panel.set_status(f"Error: {msg}", "error")
        self._set_state(IDLE)

    def on_no_audio(self):
        self._stop_timer()
        self.panel.set_status("No audio captured. Please try again.", "error")
        self._set_state(IDLE)

    def on_disconnect(self, msg):
        self._stop_timer()
        self.panel.set_status(f"Recording stopped: {msg}.", "error")
        self._set_state(IDLE)

    # --------------------------------------------------------- transcription
    def _start_transcription(self):
        self.panel.set_status("Transcribing...", "transcribing")
        self.transcription_thread = TranscriptionThread(
            self.whisper_model, self.has_loopback)
        self.transcription_thread.segment_ready.connect(self.on_segment_ready)
        self.transcription_thread.progress_update.connect(
            lambda m: self.panel.set_status(m, "transcribing"))
        self.transcription_thread.transcription_complete.connect(
            self.on_transcription_complete)
        self.transcription_thread.error_signal.connect(self.on_transcription_error)
        self.transcription_thread.start()

    def on_segment_ready(self, speaker, text):
        # Live "working" feel; replaced by ordered transcript on completion.
        self.panel.append_transcript_segment(speaker, text)

    def on_transcription_complete(self, transcript):
        self._last_transcript = transcript
        # Replace live stream with correctly time-ordered transcript (item F).
        self.panel.set_transcript(transcript)

        if not transcript.strip():
            self.panel.append_transcript_note("No speech detected in recording.")
            self.panel.set_status("Done", "done")
            self._set_state(COMPLETE)
            return

        if len(transcript.split()) < 10:
            self.panel.append_transcript_note("Note: transcript is very short.")

        if self.llm is None:
            self.panel.append_summary_text(
                "Note generation unavailable (model not loaded).")
            self.panel.set_status("Done", "done")
            self._set_state(COMPLETE)
            return

        self._start_summarization(transcript)

    def on_transcription_error(self, msg):
        self.panel.set_status(f"Error: {msg}", "error")
        self._set_state(COMPLETE)

    # --------------------------------------------------------- summarization
    def _start_summarization(self, transcript):
        self._set_state(SUMMARIZING)
        self.panel.set_status("Summarizing...", "summarizing")
        self.panel.clear_summary()
        self.summarization_thread = SummarizationThread(
            self.llm, transcript, self.training)
        self.summarization_thread.token_ready.connect(self.panel.append_summary_chunk)
        self.summarization_thread.summarization_complete.connect(
            self.on_summarization_complete)
        self.summarization_thread.summarization_error.connect(
            self.on_summarization_error)
        self.summarization_thread.start()

    def on_summarization_complete(self, full_text):
        if not full_text.strip():
            # LLM produced nothing -> treat as failure.
            self.panel.append_summary_text(
                "\n\nSummary generation failed.")
            self.panel.show_summary_retry()
        self.panel.set_status("Done", "done")
        self._set_state(COMPLETE)

    def on_summarization_error(self, msg):
        existing = self.panel.get_summary_text().strip()
        if existing:
            self.panel.append_summary_text(
                "\n\n⚠️ Generation stopped unexpectedly. Partial summary above.")
        else:
            self.panel.append_summary_text("Summary generation failed.")
        self.panel.show_summary_retry()
        self.panel.set_status("Done", "done")
        self._set_state(COMPLETE)
        log.error("Summarization error: %s", msg)

    def on_retry(self):
        if not self._last_transcript or self.llm is None:
            return
        self._start_summarization(self._last_transcript)

    # ----------------------------------------------------------- delete/save
    def on_delete(self):
        self._autosave_unsaved_notes()
        self._clear_session()
        self._set_state(IDLE)

    def on_save_notes(self):
        note = self.panel.get_notes_text().strip()
        if not note:
            return
        # Re-clicking Save with unchanged text shouldn't make a duplicate.
        if note != self._last_saved_note:
            self.training.save_example(
                transcript=self._last_transcript,
                ai_note=self.panel.get_summary_text().strip(),
                rep_note=note,
            )
            self._last_saved_note = note
        self.panel.flash_saved()

    def _autosave_unsaved_notes(self):
        note = self.panel.get_notes_text().strip()
        if note and note != self._last_saved_note:
            self.training.save_example(
                transcript=self._last_transcript,
                ai_note=self.panel.get_summary_text().strip(),
                rep_note=note,
            )
            self._last_saved_note = note

    def _clear_session(self):
        self.panel.clear_all_content()
        self.panel.set_delete_visible(False)
        self._last_transcript = ""

    # ------------------------------------------------------------- window ops
    def on_minimize(self):
        self.panel.hide()
        self.icon.show()

    def on_close_requested(self):
        if self.state == RECORDING:
            if not self._confirm_stop_recording():
                return
            self.stop_recording()
        self.panel.hide()
        self.icon.show()

    def toggle_visibility(self):
        # Show whichever surface matches the current state.
        if self.state in (TRANSCRIBING, SUMMARIZING, COMPLETE):
            target = self.panel
        else:
            target = self.icon
        if target.isVisible():
            target.hide()
        else:
            target.show()

    def quit_app(self):
        if self.state == RECORDING:
            if not self._confirm_stop_recording():
                return
            self.stop_recording()
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def _confirm_stop_recording(self) -> bool:
        box = QMessageBox(self.panel)
        box.setWindowTitle("Recording in progress")
        box.setText("Recording is in progress. Stop recording before closing?")
        keep = box.addButton("Keep Recording", QMessageBox.ButtonRole.RejectRole)
        stop = box.addButton("Stop and Close", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        return box.clickedButton() is stop

    # ------------------------------------------------------------- update ui
    def on_update_available(self, version):
        self.panel.show_update_banner(version)

    def on_download_update(self):
        webbrowser.open(f"https://github.com/{GITHUB_REPO}/releases/latest")

    # ---------------------------------------------------------------- timer
    def _start_timer(self):
        self._record_start = time.time()
        self.icon.set_timer_text("00:00")
        self.panel.set_timer("00:00")
        self._timer.start(1000)

    def _stop_timer(self):
        self._timer.stop()
        self._record_start = None
        self.icon.set_timer_text("")
        self.panel.set_timer("00:00")

    def _tick(self):
        if self._record_start is None:
            return
        elapsed = int(time.time() - self._record_start)
        m, s = divmod(elapsed, 60)
        text = f"{m:02d}:{s:02d}"
        self.icon.set_timer_text(text)
        self.panel.set_timer(text)

        # Correction G: use >= with a guard so a skipped tick can't miss it.
        if elapsed >= TWO_HOURS:
            self.stop_recording()
            self.panel.set_status("Recording auto-stopped at 2 hours.", "done")
        elif elapsed >= ONE_HOUR and not self._one_hour_warned:
            self._one_hour_warned = True
            self.panel.set_status("Recording for 1 hour — still recording?", "recording")

    # ------------------------------------------------------------- helpers
    def _set_state(self, new_state):
        log.info("State: %s -> %s", self.state, new_state)
        self.state = new_state
        if new_state == IDLE:
            self.panel.hide()
            self.icon.show()
            self.icon.show_idle()
            self.panel.set_delete_visible(False)
            self.panel.set_record_button_recording(False)
        elif new_state == RECORDING:
            self.panel.hide()
            self.icon.show()
            self.icon.show_recording()
            self.panel.set_status("Recording...", "recording")
            self.panel.set_record_button_recording(True)
            self.panel.set_delete_visible(False)
        elif new_state in (TRANSCRIBING, SUMMARIZING):
            self.icon.show_idle()
            self.panel.set_record_button_recording(False)
            self.panel.set_delete_visible(False)
        elif new_state == COMPLETE:
            self.panel.set_record_button_recording(False)
            self.panel.set_delete_visible(True)

    def _show_panel(self):
        self.icon.hide()
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()

    def _copy(self, text):
        if text:
            pyperclip.copy(text)

    def _save_geometry(self):
        g = self.panel.geometry()
        self.config.save_window_geometry(g.x(), g.y(), g.width(), g.height())
