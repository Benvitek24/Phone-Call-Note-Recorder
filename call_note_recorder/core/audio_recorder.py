"""Dual-stream WASAPI recording.

Mic  -> "You"      | Loopback -> "Customer"
The two streams are NEVER mixed (spec hard rule). Each is saved to its own WAV.

Corrections folded in:
  (C) Loopback devices are almost always multi-channel (they mirror the output
      device). We open each stream at the device's real channel count and
      DOWNMIX TO MONO when saving. Downmixing the channels *within one stream*
      is fine — it is not the forbidden mic+loopback mixing.
  (disconnect) If a device drops mid-recording, the read raises; we flag it and
      stop both streams so the UI can show the disconnect error.
"""

import threading
import wave

import numpy as np
import pyaudiowpatch as pyaudio
from scipy import signal as sp_signal

from PyQt6.QtCore import QThread, pyqtSignal

from utils.paths import MIC_WAV, LOOPBACK_WAV
from utils.logger import get_logger

log = get_logger("audio")

TARGET_SAMPLE_RATE = 16000   # Whisper requires 16 kHz mono
CHUNK = 1024


def detect_devices():
    """Return (mic_info, loopback_info). loopback_info may be None.

    mic_info may also be None if the machine has no input device — the caller
    must handle that ("No microphone detected").
    """
    p = pyaudio.PyAudio()
    try:
        mic = None
        try:
            mic = p.get_default_input_device_info()
        except (OSError, IOError) as e:
            log.warning("No default input device: %s", e)

        loopback = None
        try:
            default_output = p.get_default_output_device_info()
            output_name = str(default_output['name'])[:15]
        except (OSError, IOError):
            output_name = ""

        # Preferred: the loopback that matches the default output device.
        if output_name:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if '[Loopback]' in info['name'] and output_name in info['name']:
                    loopback = info
                    break

        # Fallback: any loopback device.
        if loopback is None:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if '[Loopback]' in info['name']:
                    loopback = info
                    break

        return mic, loopback
    finally:
        p.terminate()


class RecordingThread(QThread):
    error_signal     = pyqtSignal(str)   # fatal error message
    disconnect_signal = pyqtSignal(str)  # device dropped mid-recording
    no_audio_signal  = pyqtSignal()      # stopped but nothing was captured
    stopped_signal   = pyqtSignal(bool)  # emitted when WAVs ready; arg=has_loopback

    def __init__(self, mic_device, loopback_device):
        super().__init__()
        self.mic_device      = mic_device
        self.loopback_device = loopback_device
        self._stop_flag      = False
        self._disconnected   = False
        self.mic_frames      = []
        self.loopback_frames = []

    def run(self):
        p = pyaudio.PyAudio()
        try:
            mic_rate = int(self.mic_device['defaultSampleRate'])
            mic_ch   = max(1, int(self.mic_device.get('maxInputChannels', 1)))

            threads = [threading.Thread(
                target=self._record_stream,
                args=(p, self.mic_device, self.mic_frames, mic_rate, mic_ch),
                daemon=True,
            )]

            lb_rate = lb_ch = None
            if self.loopback_device:
                lb_rate = int(self.loopback_device['defaultSampleRate'])
                lb_ch   = max(1, int(self.loopback_device.get('maxInputChannels', 2)))
                threads.append(threading.Thread(
                    target=self._record_stream,
                    args=(p, self.loopback_device, self.loopback_frames, lb_rate, lb_ch),
                    daemon=True,
                ))

            for t in threads:
                t.start()
            for t in threads:
                t.join()

        except Exception as e:  # noqa: BLE001 - surface any setup failure to UI
            log.exception("Recording failed")
            p.terminate()
            self.error_signal.emit(str(e))
            return
        finally:
            try:
                p.terminate()
            except Exception:  # noqa: BLE001
                pass

        if self._disconnected:
            self.disconnect_signal.emit("audio device disconnected")
            return

        # Nothing captured at all -> distinct "no audio" path (back to IDLE).
        if not self.mic_frames and not self.loopback_frames:
            self.no_audio_signal.emit()
            return

        # Persist WAVs (downmixed to mono, resampled to 16 kHz).
        try:
            if self.mic_frames:
                self._save_wav(self.mic_frames, MIC_WAV, mic_rate, mic_ch)
            has_loopback = bool(self.loopback_frames)
            if has_loopback:
                self._save_wav(self.loopback_frames, LOOPBACK_WAV, lb_rate, lb_ch)
        except Exception as e:  # noqa: BLE001
            log.exception("Saving WAV failed")
            self.error_signal.emit(str(e))
            return

        self.stopped_signal.emit(has_loopback)

    def _record_stream(self, p, device_info, frames_list, sample_rate, channels):
        stream = None
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=int(sample_rate),
                input=True,
                input_device_index=int(device_info['index']),
                frames_per_buffer=CHUNK,
            )
            while not self._stop_flag:
                try:
                    frames_list.append(
                        stream.read(CHUNK, exception_on_overflow=False)
                    )
                except (OSError, IOError):
                    # Device removed / unplugged mid-recording.
                    self._disconnected = True
                    self._stop_flag = True
                    break
        except Exception as e:  # noqa: BLE001
            log.exception("Stream open/read failed for %s", device_info.get('name'))
            self._disconnected = True
            self._stop_flag = True
            self.error_signal.emit(str(e))
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:  # noqa: BLE001
                    pass

    def stop(self):
        self._stop_flag = True

    @staticmethod
    def _save_wav(frames, path, source_rate, channels):
        raw = b''.join(frames)
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)

        # Downmix interleaved channels -> mono (average across channels).
        if channels > 1:
            usable = (len(audio) // channels) * channels
            audio = audio[:usable].reshape(-1, channels).mean(axis=1)

        # Resample to 16 kHz for Whisper.
        if source_rate != TARGET_SAMPLE_RATE and len(audio) > 0:
            num = int(round(len(audio) * TARGET_SAMPLE_RATE / source_rate))
            audio = sp_signal.resample(audio, num)

        audio = np.clip(audio, -32768, 32767).astype(np.int16)

        with wave.open(path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(TARGET_SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
