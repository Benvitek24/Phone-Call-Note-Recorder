"""faster-whisper transcription.

Each stream is transcribed separately and labeled by source (mic="You",
loopback="Customer"), then merged by timestamp into the final transcript.

Correction folded in (review item F): the live `segment_ready` stream fires per
file, so during processing the user sees all "You" lines then all "Customer"
lines. To avoid a jarring reshuffle, the UI shows the live stream for the
"working" feel, then on `transcription_complete` REPLACES it with the correctly
time-ordered merged transcript.
"""

import os

from PyQt6.QtCore import QThread, pyqtSignal

from utils.paths import MIC_WAV, LOOPBACK_WAV
from utils.logger import get_logger

log = get_logger("transcription")

# Transcripts longer than this (characters) are truncated before the LLM so the
# prompt stays within n_ctx. Display keeps the full transcript.
LLM_TRANSCRIPT_BUDGET = 9000


class TranscriptionThread(QThread):
    segment_ready          = pyqtSignal(str, str)  # speaker, text (live feel)
    transcription_complete = pyqtSignal(str)        # final merged transcript
    progress_update        = pyqtSignal(str)
    error_signal           = pyqtSignal(str)

    def __init__(self, whisper_model, has_loopback):
        super().__init__()
        self.model        = whisper_model
        self.has_loopback = has_loopback

    def run(self):
        try:
            mic_segments = self._transcribe(MIC_WAV, "You",
                                            "Transcribing your audio...")

            loopback_segments = []
            if self.has_loopback and os.path.exists(LOOPBACK_WAV):
                loopback_segments = self._transcribe(
                    LOOPBACK_WAV, "Customer", "Transcribing customer audio..."
                )

            transcript = self._merge_and_format(mic_segments, loopback_segments)

            for path in (MIC_WAV, LOOPBACK_WAV):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass

            self.transcription_complete.emit(transcript)
        except Exception as e:  # noqa: BLE001
            log.exception("Transcription failed")
            self.error_signal.emit(str(e))

    def _transcribe(self, wav_path, speaker, progress_msg):
        segments_out = []
        if not os.path.exists(wav_path):
            return segments_out
        self.progress_update.emit(progress_msg)
        segments, _info = self.model.transcribe(wav_path, language="en", beam_size=5)
        for seg in segments:  # generator -> processed incrementally
            text = seg.text.strip()
            if not text:
                continue
            segments_out.append(
                {"speaker": speaker, "text": text, "start": seg.start, "end": seg.end}
            )
            self.segment_ready.emit(speaker, text)
        return segments_out

    @staticmethod
    def _merge_and_format(mic_segs, loopback_segs):
        all_segs = [s for s in (mic_segs + loopback_segs) if s["text"]]
        all_segs.sort(key=lambda s: s["start"])
        if not all_segs:
            return ""

        lines = []
        current_speaker = None
        current_texts = []
        for seg in all_segs:
            if seg["speaker"] != current_speaker:
                if current_speaker and current_texts:
                    lines.append(f"{current_speaker}: {' '.join(current_texts)}")
                current_speaker = seg["speaker"]
                current_texts = [seg["text"]]
            else:
                current_texts.append(seg["text"])
        if current_speaker and current_texts:
            lines.append(f"{current_speaker}: {' '.join(current_texts)}")

        return "\n\n".join(lines)


def transcript_for_llm(transcript: str) -> str:
    """Cap the transcript fed to the LLM so the prompt fits in context.
    Keeps the start and end of the call (where intent and next steps live)."""
    t = (transcript or "").strip()
    if len(t) <= LLM_TRANSCRIPT_BUDGET:
        return t
    head = t[: int(LLM_TRANSCRIPT_BUDGET * 0.6)].rstrip()
    tail = t[-int(LLM_TRANSCRIPT_BUDGET * 0.4):].lstrip()
    return f"{head}\n\n[...middle of call omitted for length...]\n\n{tail}"
