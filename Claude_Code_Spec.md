# Call Note Recorder — Claude Code Implementation Spec
**Version: 1.0**
**Status: READY FOR IMPLEMENTATION**

---

## WHAT YOU ARE BUILDING

A local Windows desktop application for Keyence inside sales representatives.
The app records Microsoft Teams phone calls, transcribes both sides with speaker
labels, generates AI-written CRM notes, and streams them word by word in real
time. It includes a per-user training loop that improves note quality over time.

**The entire stack runs locally on the machine. No cloud. No API calls. No
subscriptions. No external services.**

---

## READ THIS SECTION FIRST — CRITICAL CONSTRAINTS

These are hard rules. Do not deviate from them.

### 1. UI Framework
- **USE:** PyQt6 exclusively
- **DO NOT USE:** pywebview, Tkinter, wxPython, web-based UI of any kind
- Reason: precise window control, native Win32 access, proper threading signals

### 2. LLM Runtime
- **USE:** llama-cpp-python running inside the Python process
- **DO NOT USE:** Ollama, any external service, any background service
- Reason: 80 sales reps — no one will manage a background service

### 3. Audio Streams
- **ALWAYS keep mic and loopback as separate streams**
- **NEVER mix or combine audio before transcription**
- Mic → transcribed as "You" | Loopback → transcribed as "Customer"
- Reason: mixing destroys all speaker information

### 4. llama-cpp-python Build — CRITICAL
All pre-built wheels crash on 12th Gen Intel (Alder Lake) with
`OSError: [WinError -1073741795] Windows Error 0xc000001d`
Root cause: Alder Lake has no AVX-512. All pre-built wheels have AVX-512 on.

**llama-cpp-python MUST be installed from source with these exact flags:**
```
set CMAKE_ARGS=-DGGML_AVX512=OFF -DGGML_AVX512_VBMI=OFF -DGGML_AVX512_VNNI=OFF -DGGML_AMX_TILE=OFF -DGGML_AMX_INT8=OFF -DGGML_AMX_BF16=OFF -DGGML_AVX2=ON -DGGML_AVX=ON -DGGML_FMA=ON
python -m pip install llama-cpp-python --no-binary llama-cpp-python
```

Prerequisites before source build:
1. Enable Windows Long Paths (run as admin):
   `reg add "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1 /f`
2. VS Build Tools 2022 with C++ workload must be installed

### 5. LLM Runs on CPU — Intentional
`n_gpu_layers=0` always. Confirmed: 0.9 seconds for a full CRM note on
i9-12950HX. GPU acceleration not needed and adds complexity. Do not add CUDA
to llama-cpp-python.

### 6. torch PATH Required
llama-cpp-python's DLL needs this in PATH to load:
```
C:\Users\[user]\AppData\Local\Programs\Python\Python311\Lib\site-packages\torch\lib
```
This is already set permanently on the target machine. The installer must
handle this for other machines.

### 7. No Hardcoded Paths
Never hardcode any user or system path.
- Use `os.environ['APPDATA']` for app storage
- Use `os.environ['USERNAME']` for per-user data
- Use `os.path.expanduser()` for anything user-relative
- The Desktop is `C:\Users\[user]\OneDrive - KEYENCE\Desktop` — NOT standard

### 8. No Animation
Do not implement animated window transitions. Use instant state changes only.
Animated resizing was the source of multiple unfixable bugs in v1. Not worth
the complexity.

### 9. Zscaler SSL
All HTTPS on corporate machines goes through Zscaler SSL inspection.
pip-system-certs is installed and handles this for runtime HTTPS calls.
Any `requests` call will work correctly. Installer must bundle all packages.

---

## CONFIRMED ENVIRONMENT

```
Machine    : Dell Precision 7670 (KAVITEKB.keyence.com)
OS         : Windows 11 Enterprise Build 10.0.26200
CPU        : Intel i9-12950HX (12th Gen Alder Lake — NO AVX-512)
RAM        : 64GB
GPU        : NVIDIA RTX A2000 8GB Laptop
Driver     : 581.95 | CUDA 13.0
Python     : 3.11.9
Domain     : keyence.com
Admin      : YES
```

**Confirmed working packages (already installed on target machine):**
```
PyQt6                 6.11.0
pyaudiowpatch         0.2.12.8
faster-whisper        1.2.1
llama-cpp-python      0.3.28  (source build, CPU only)
pyperclip             1.11.0
pip-system-certs      5.3
torch                 2.5.1+cu121
scipy                 (latest)
numpy                 2.4.6
```

**Confirmed working audio device:**
- Mic input:  "Headset Microphone (Zone Vibe 125)"
- Loopback:   "Headset Earphone (Zone Vibe 125) [Loopback]"

**Confirmed model:**
- Path: `%APPDATA%\CallNoteRecorder\models\Llama-3.2-3B-Instruct-Q4_K_M.gguf`
- Size: 2.0GB
- Inference: 0.9 seconds on i9-12950HX CPU

---

## TECH STACK

| Component | Library | Version | Notes |
|-----------|---------|---------|-------|
| UI | PyQt6 | 6.11.0 | All windows, widgets, threading |
| Glassmorphic blur | Win32 DWM API via ctypes | — | Applied after window shown |
| Audio capture | pyaudiowpatch | 0.2.12.8 | WASAPI loopback support |
| Transcription | faster-whisper | 1.2.1 | CUDA GPU, small model |
| LLM | llama-cpp-python | 0.3.28 | CPU only, source build |
| LLM model | Llama 3.2 3B Q4_K_M GGUF | — | In %APPDATA% |
| Clipboard | pyperclip | 1.11.0 | Copy buttons |
| Audio processing | scipy + numpy | — | Resampling only, no mixing |
| Config + storage | json stdlib | — | No extra dependencies |
| Threading | QThread + pyqtSignal | — | Native Qt, not threading.Thread |
| System tray | PyQt6.QtWidgets.QSystemTrayIcon | — | |
| Updates | requests + GitHub Releases API | — | pip-system-certs handles SSL |
| Logging | logging.handlers.RotatingFileHandler | — | |
| Unique IDs | uuid stdlib | — | Training data record IDs |

---

## FILE AND FOLDER STRUCTURE

### Application Source
```
call_note_recorder/
├── main.py                    # Entry point — creates QApplication, launches app
├── version.py                 # APP_VERSION, GITHUB_REPO constants
├── app/
│   ├── __init__.py
│   ├── main_window.py         # Root window managing state transitions
│   ├── icon_widget.py         # Small floating glassmorphic button
│   ├── panel_widget.py        # Full 3-column panel
│   ├── tray_manager.py        # System tray icon and menu
│   └── styles.py              # All QSS stylesheets as constants
├── core/
│   ├── __init__.py
│   ├── audio_recorder.py      # pyaudiowpatch recording, dual-stream
│   ├── transcription.py       # faster-whisper pipeline, segment merging
│   ├── llm_engine.py          # llama-cpp-python, streaming, prompt builder
│   └── update_checker.py      # GitHub Releases API check
├── data/
│   ├── __init__.py
│   ├── training_store.py      # Load/save training_data JSON
│   └── config_store.py        # Load/save config JSON, window position
└── utils/
    ├── __init__.py
    ├── paths.py               # All path constants — no paths elsewhere
    └── logger.py              # Logging setup
```

### AppData Storage (runtime)
```
%APPDATA%\CallNoteRecorder\
├── models\
│   └── Llama-3.2-3B-Instruct-Q4_K_M.gguf
├── training_data\
│   └── [USERNAME].json           # One file per Windows user
├── logs\
│   └── app.log                   # Rotating, max 5MB, keep 3 backups
├── temp\
│   ├── mic.wav                   # Deleted after transcription
│   └── loopback.wav              # Deleted after transcription
└── config.json                   # Window position, size, device prefs
```

### utils/paths.py — Single source for all paths
```python
import os

APPDATA_BASE    = os.path.join(os.environ['APPDATA'], 'CallNoteRecorder')
MODELS_DIR      = os.path.join(APPDATA_BASE, 'models')
TRAINING_DIR    = os.path.join(APPDATA_BASE, 'training_data')
LOGS_DIR        = os.path.join(APPDATA_BASE, 'logs')
TEMP_DIR        = os.path.join(APPDATA_BASE, 'temp')
CONFIG_FILE     = os.path.join(APPDATA_BASE, 'config.json')
MODEL_FILE      = os.path.join(MODELS_DIR, 'Llama-3.2-3B-Instruct-Q4_K_M.gguf')
MIC_WAV         = os.path.join(TEMP_DIR, 'mic.wav')
LOOPBACK_WAV    = os.path.join(TEMP_DIR, 'loopback.wav')
USERNAME        = os.environ.get('USERNAME', 'default')
TRAINING_FILE   = os.path.join(TRAINING_DIR, f'{USERNAME}.json')

def ensure_dirs():
    for d in [MODELS_DIR, TRAINING_DIR, LOGS_DIR, TEMP_DIR]:
        os.makedirs(d, exist_ok=True)
```

---

## APP STARTUP SEQUENCE

Execute in this exact order:

```
1. Call paths.ensure_dirs()
2. Set up rotating log file
3. Load config.json (create with defaults if missing)
4. Create QApplication
5. Create system tray icon
6. Show small floating icon widget (record button greyed out, "Loading..." tooltip)
7. Start ModelLoaderThread (loads Whisper + LLM in background)
8. Start UpdateCheckThread (GitHub API check)
9. Enter Qt event loop
10. When ModelLoaderThread completes → enable record button, set tooltip "Ready"
11. When UpdateCheckThread finds update → show update banner in top bar
```

While models load (step 7), the UI is visible and usable but recording is
disabled. Show a subtle loading indicator (e.g., animated dots in status text).
Model loading takes approximately 3-8 seconds on target hardware.

---

## APPLICATION STATE MACHINE

The app has exactly these states. Only the listed transitions are valid.

```
IDLE
  → RECORDING       (record button pressed, models loaded)

RECORDING
  → IDLE            (error: no audio captured)
  → TRANSCRIBING    (stop button pressed, audio saved)

TRANSCRIBING
  → SUMMARIZING     (transcription complete, transcript not empty)
  → COMPLETE        (transcription complete but empty — show error)

SUMMARIZING
  → COMPLETE        (summary complete OR partial failure)

COMPLETE
  → IDLE            (delete button pressed)
  → RECORDING       (record button pressed — auto-clears current session)
```

**State controls what's visible:**
- IDLE:           Icon widget only
- RECORDING:      Icon widget (red + pulsing + timer)
- TRANSCRIBING:   Panel visible, transcript column active, progress in top bar
- SUMMARIZING:    Panel visible, all columns active, summary streaming
- COMPLETE:       Panel visible, all columns populated, ready to copy

---

## UI SPECIFICATION

### Window Architecture

Two separate QWidget windows:
1. `IconWidget` — the small floating button (always present when app running)
2. `PanelWidget` — the expanded 3-column panel

Both are frameless, transparent, always-on-top (panel only when expanded),
with Win32 Acrylic blur applied.

### Icon Widget

```
Size:       68 × 68 px (fixed, not resizable)
Position:   Bottom-right of primary screen, 20px from each edge
Shape:      Rounded rectangle, radius 18px
Background: rgba(28, 28, 30, 0.88) + Win32 Acrylic blur
Border:     1px rgba(255, 255, 255, 0.12)

Contents when IDLE:
  - Centered circle button, 36px diameter
  - Grey fill: rgba(255, 255, 255, 0.15)
  - Icon: ● (record symbol)

Contents when RECORDING:
  - Same button, fill: #FF3B30
  - Pulse animation: opacity oscillates 60%→100% at 1.2s period
  - Timer text below button: "01:23" monospace, 10px, #AAAAAA

Always-on-top: NO (icon stays below other windows when minimized)
```

**Pulse animation using QTimer:**
```python
self._pulse_timer = QTimer()
self._pulse_timer.timeout.connect(self._pulse_step)
self._pulse_value = 255
self._pulse_direction = -1

def _pulse_step(self):
    self._pulse_value += self._pulse_direction * 8
    if self._pulse_value <= 140:
        self._pulse_direction = 1
    elif self._pulse_value >= 255:
        self._pulse_direction = -1
    alpha = self._pulse_value / 255.0
    self.record_btn.setStyleSheet(
        f"background-color: rgba(255, 59, 48, {alpha:.2f}); border-radius: 18px;"
    )

# Start: self._pulse_timer.start(30)
# Stop:  self._pulse_timer.stop()
```

### Panel Widget

```
Default size:   40% of screen width × 35% of screen height
Minimum size:   600 × 350 px (enforced via setMinimumSize)
Maximum width:  50% of screen width (enforced via setMaximumWidth)
Position:       Bottom-right anchored — bottom-right corner of panel is
                always 20px from bottom-right of screen on first open.
                After first open, position is remembered via config.json.
Resizable:      YES — user can drag all edges freely
Always-on-top:  YES — Qt.WindowType.WindowStaysOnTopHint
Background:     rgba(20, 20, 22, 0.90) + Win32 Acrylic blur
Border:         1px rgba(255, 255, 255, 0.10)
Corner radius:  12px
```

**Initial position calculation:**
```python
screen = QApplication.primaryScreen().availableGeometry()
x = screen.right() - self.width() - 20
y = screen.bottom() - self.height() - 20
self.move(x, y)
```

**Position memory:** Save geometry to config.json on every moveEvent and
resizeEvent. Restore from config.json on startup. If saved position is
off-screen (after monitor change), fall back to default bottom-right.

### Panel — Top Bar
```
Height:     44px
Background: rgba(15, 15, 17, 0.95)
Border-bottom: 1px rgba(255, 255, 255, 0.08)

Layout (left to right):
  [12px padding]
  [●/■] Record/Stop button — 28px circle
  [8px gap]
  [00:00] Timer — monospace, 13px, #CCCCCC, min-width 44px
  [12px gap]
  [Status text] — 13px, color changes by state (see Status Colors)
  [stretch spacer]
  [Delete] button — only visible in COMPLETE state
  [8px gap]
  [─] Minimize button
  [4px gap]
  [✕] Close button
  [12px padding]
```

**Status Colors:**
```
"Loading..."      #888888
"Ready"           #888888
"Recording..."    #FF3B30
"Transcribing..."  #FF9F0A
"Summarizing..."  #30D158
"Done"            #888888
"Error: [msg]"    #FF3B30
```

### Panel — Column Layout
```
Three equal-width columns by default, separated by 1px rgba(255,255,255,0.07)

Each column structure:
  [Column header button — 36px height, full width]
    Text: "Transcript ▾" | "Summary ▾" | "My Notes ▾"
    Background: rgba(35, 35, 38, 0.6)
    Font: 12px, #CCCCCC, medium weight
    Clicking collapses/expands the column

  [Scrollable content area — fills remaining height]
    Background: transparent
    Padding: 12px
    Font: 13px, #F0F0F0, line-height 1.6
    Scrollbar: thin, styled dark
    Transcript + Summary: QLabel or QTextEdit (read-only) 
    My Notes: QTextEdit (editable, placeholder: "Type your own note here...")

  [Bottom action bar — 36px height]
    Background: rgba(15, 15, 17, 0.6)
    Transcript: [Copy] button right-aligned
    Summary:    [Copy] button right-aligned
    My Notes:   [Save] button left-aligned, [Copy] button right-aligned
```

**Column collapse behavior:**
- Collapsed column: header visible only, width = 32px (just the label rotated
  90° or abbreviated)
- Other columns redistribute space equally
- If all three collapsed: not possible — at least one must stay open (disable
  collapse button of last open column)

**When one column takes full width:**
- Not triggered automatically
- User-controlled via column collapse

### Buttons (consistent styling)

```
Standard button (Copy, Save, Delete, Minimize, Close):
  Background:    rgba(255, 255, 255, 0.08)
  Hover:         rgba(255, 255, 255, 0.14)
  Pressed:       rgba(255, 255, 255, 0.20)
  Border-radius: 6px
  Border:        1px rgba(255, 255, 255, 0.10)
  Font:          12px, #DDDDDD
  Padding:       4px 10px

Delete button (when visible):
  Background:    rgba(255, 59, 48, 0.15)
  Hover:         rgba(255, 59, 48, 0.25)
  Border:        1px rgba(255, 59, 48, 0.30)
  Color:         #FF3B30

Close [✕] button:
  Hover background: rgba(255, 59, 48, 0.20)
```

### Win32 Acrylic Effect

Apply to both IconWidget and PanelWidget after window is shown:

```python
import ctypes

def apply_acrylic(hwnd: int):
    """Apply Windows 11 Acrylic blur behind window."""
    try:
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_SYSTEMBACKDROP_TYPE = 38
        DWMSBT_ACRYLIC = 3

        # Enable dark mode title bar
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(1)),
            ctypes.sizeof(ctypes.c_int)
        )

        # Apply acrylic backdrop
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(ctypes.c_int(DWMSBT_ACRYLIC)),
            ctypes.sizeof(ctypes.c_int)
        )
    except Exception as e:
        # Fallback: semi-transparent background only (still looks good)
        pass
```

**Required Qt window setup for acrylic to work:**
```python
self.setWindowFlags(
    Qt.WindowType.FramelessWindowHint |
    Qt.WindowType.WindowStaysOnTopHint |
    Qt.WindowType.Tool  # Keeps out of taskbar
)
self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
```

**Call apply_acrylic in showEvent:**
```python
def showEvent(self, event):
    super().showEvent(event)
    hwnd = int(self.winId())
    apply_acrylic(hwnd)
```

### Frameless Window — Drag to Move

Since the window is frameless, implement drag-to-move on the top bar:

```python
def mousePressEvent(self, event):
    if event.button() == Qt.MouseButton.LeftButton:
        self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

def mouseMoveEvent(self, event):
    if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
        self.move(event.globalPosition().toPoint() - self._drag_pos)

def mouseReleaseEvent(self, event):
    self._drag_pos = None
    self._save_geometry()  # Persist position to config
```

Only apply drag logic when the cursor is on the top bar (y < 44px).

### Frameless Window — Resize Handles

Implement resize by detecting cursor proximity to edges:

```python
RESIZE_MARGIN = 8  # px from edge to trigger resize cursor

def mouseMoveEvent(self, event):
    pos = event.position().toPoint()
    # Determine resize zone and change cursor
    on_left   = pos.x() < RESIZE_MARGIN
    on_top    = pos.y() < RESIZE_MARGIN
    on_right  = pos.x() > self.width() - RESIZE_MARGIN
    on_bottom = pos.y() > self.height() - RESIZE_MARGIN

    if (on_left and on_top) or (on_right and on_bottom):
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
    elif (on_right and on_top) or (on_left and on_bottom):
        self.setCursor(Qt.CursorShape.SizeBDiagCursor)
    elif on_left or on_right:
        self.setCursor(Qt.CursorShape.SizeHorCursor)
    elif on_top or on_bottom:
        self.setCursor(Qt.CursorShape.SizeVerCursor)
    else:
        self.setCursor(Qt.CursorShape.ArrowCursor)
```

Handle the actual resize geometry changes in mousePress/Move/Release using the
same zone detection. Enforce minimum size (600×350) during resize.

---

## SYSTEM TRAY

```python
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction

class TrayManager:
    def __init__(self, app_controller):
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon(TRAY_ICON_PATH))
        self.tray.setToolTip("Call Note Recorder")

        menu = QMenu()
        show_action  = QAction("Show / Hide")
        quit_action  = QAction("Quit")

        show_action.triggered.connect(app_controller.toggle_visibility)
        quit_action.triggered.connect(app_controller.quit_app)

        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        self.tray.show()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.app_controller.toggle_visibility()
```

**Close behavior:**
- Clicking [✕] on panel: if recording active → show warning dialog. Otherwise
  hide to tray (do not quit).
- Quit from tray menu: if recording active → show warning dialog. Otherwise
  quit fully.
- Warning dialog text: "Recording is in progress. Stop recording before closing?"
  Buttons: [Keep Recording] [Stop and Close]

---

## AUDIO PIPELINE

### Step 1 — Device Detection

```python
import pyaudiowpatch as pyaudio

def detect_devices():
    """
    Returns: (mic_device_info, loopback_device_info)
    loopback_device_info may be None if no loopback found.
    """
    p = pyaudio.PyAudio()
    
    try:
        # Get default output device
        default_output = p.get_default_output_device_info()
        output_name = default_output['name'][:20]  # First 20 chars for matching
        
        # Find corresponding loopback
        loopback = None
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if '[Loopback]' in info['name'] and output_name[:15] in info['name']:
                loopback = info
                break
        
        # Fallback: any loopback device
        if not loopback:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if '[Loopback]' in info['name']:
                    loopback = info
                    break
        
        # Default mic
        mic = p.get_default_input_device_info()
        
        return mic, loopback
    
    finally:
        p.terminate()
```

**If loopback is None:** Show the no-loopback warning banner (see Error
Handling), record mic only, label all transcript text as "You:".

### Step 2 — Recording

Run in `RecordingThread(QThread)`. Two streams run concurrently using Python
threading.Thread within the QThread worker:

```python
TARGET_SAMPLE_RATE = 16000  # Whisper requires 16kHz
CHUNK = 1024

class RecordingThread(QThread):
    error_signal   = pyqtSignal(str)
    stopped_signal = pyqtSignal()  # Emitted when audio files are ready

    def __init__(self, mic_device, loopback_device):
        super().__init__()
        self.mic_device      = mic_device
        self.loopback_device = loopback_device
        self._stop_flag      = False
        self.mic_frames      = []
        self.loopback_frames = []

    def run(self):
        p = pyaudio.PyAudio()
        import threading

        def record_stream(device_info, frames_list, sample_rate):
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=int(sample_rate),
                input=True,
                input_device_index=int(device_info['index']),
                frames_per_buffer=CHUNK
            )
            while not self._stop_flag:
                frames_list.append(stream.read(CHUNK, exception_on_overflow=False))
            stream.stop_stream()
            stream.close()

        mic_rate = int(self.mic_device['defaultSampleRate'])
        
        threads = [
            threading.Thread(
                target=record_stream,
                args=(self.mic_device, self.mic_frames, mic_rate)
            )
        ]
        
        if self.loopback_device:
            lb_rate = int(self.loopback_device['defaultSampleRate'])
            threads.append(threading.Thread(
                target=record_stream,
                args=(self.loopback_device, self.loopback_frames, lb_rate)
            ))
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        p.terminate()
        
        # Save WAV files
        self._save_wav(self.mic_frames, MIC_WAV, mic_rate)
        if self.loopback_frames:
            self._save_wav(self.loopback_frames, LOOPBACK_WAV, lb_rate)
        
        self.stopped_signal.emit()

    def stop(self):
        self._stop_flag = True

    def _save_wav(self, frames, path, source_rate):
        import wave, numpy as np
        from scipy import signal as sp
        
        audio = np.frombuffer(b''.join(frames), dtype=np.int16).astype(np.float32)
        
        if source_rate != TARGET_SAMPLE_RATE:
            num = int(len(audio) * TARGET_SAMPLE_RATE / source_rate)
            audio = sp.resample(audio, num)
        
        audio = np.clip(audio, -32768, 32767).astype(np.int16)
        
        with wave.open(path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(TARGET_SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
```

---

## TRANSCRIPTION PIPELINE

### WhisperModel Loading

Load once at app startup in a background thread. Store as app-level singleton.
Do NOT reload on every transcription.

```python
from faster_whisper import WhisperModel

# Load at startup (in ModelLoaderThread):
whisper_model = WhisperModel("small", device="cuda", compute_type="float16")
```

### TranscriptionThread

```python
class TranscriptionThread(QThread):
    segment_ready          = pyqtSignal(str, str)  # speaker, text
    transcription_complete = pyqtSignal(str)        # full formatted transcript
    progress_update        = pyqtSignal(str)        # status message
    error_signal           = pyqtSignal(str)

    def __init__(self, whisper_model, has_loopback):
        super().__init__()
        self.model       = whisper_model
        self.has_loopback = has_loopback

    def run(self):
        try:
            mic_segments      = []
            loopback_segments = []

            # Transcribe mic (You)
            self.progress_update.emit("Transcribing your audio...")
            segments, _ = self.model.transcribe(
                MIC_WAV, language="en", beam_size=5
            )
            for seg in segments:
                entry = {
                    "speaker": "You",
                    "text":    seg.text.strip(),
                    "start":   seg.start,
                    "end":     seg.end
                }
                mic_segments.append(entry)
                self.segment_ready.emit("You", seg.text.strip())

            # Transcribe loopback (Customer)
            if self.has_loopback and os.path.exists(LOOPBACK_WAV):
                self.progress_update.emit("Transcribing customer audio...")
                segments, _ = self.model.transcribe(
                    LOOPBACK_WAV, language="en", beam_size=5
                )
                for seg in segments:
                    entry = {
                        "speaker": "Customer",
                        "text":    seg.text.strip(),
                        "start":   seg.start,
                        "end":     seg.end
                    }
                    loopback_segments.append(entry)
                    self.segment_ready.emit("Customer", seg.text.strip())

            # Merge and format
            transcript = self._merge_and_format(mic_segments, loopback_segments)

            # Clean up temp files
            for path in [MIC_WAV, LOOPBACK_WAV]:
                if os.path.exists(path):
                    os.remove(path)

            self.transcription_complete.emit(transcript)

        except Exception as e:
            self.error_signal.emit(str(e))

    def _merge_and_format(self, mic_segs, loopback_segs):
        """Merge by timestamp, group consecutive same-speaker segments."""
        all_segs = mic_segs + loopback_segs
        all_segs.sort(key=lambda s: s['start'])

        if not all_segs:
            return ""

        lines = []
        current_speaker = None
        current_texts   = []

        for seg in all_segs:
            if seg['text'] == "":
                continue
            if seg['speaker'] != current_speaker:
                if current_speaker and current_texts:
                    lines.append(f"{current_speaker}: {' '.join(current_texts)}")
                current_speaker = seg['speaker']
                current_texts   = [seg['text']]
            else:
                current_texts.append(seg['text'])

        if current_speaker and current_texts:
            lines.append(f"{current_speaker}: {' '.join(current_texts)}")

        return "\n\n".join(lines)
```

**Real-time display:** The `segment_ready` signal fires as each segment
completes. Connect it to a slot that appends to the transcript panel with the
label and text. This gives the "appearing as it processes" feel.

---

## LLM PIPELINE

### LLM Loading

Load at startup in ModelLoaderThread, same as Whisper:

```python
from llama_cpp import Llama

llm = Llama(
    model_path=MODEL_FILE,
    n_gpu_layers=0,       # CPU only — intentional
    n_ctx=4096,           # Enough for transcript + prompt + output
    verbose=False
)
```

### Prompt Template

```python
SYSTEM_PROMPT = """You are a CRM note writer for a Keyence inside sales representative.

Rules:
- Write in lowercase
- Write conversationally, not like formal business writing
- Write in third person about the customer
- Keep notes short — if the call was short, the note is short
- Capture only what was explicitly discussed: why they called, the customer's application, products mentioned, what happens next
- Never add information not stated in the transcript
- Never pad with filler phrases or pleasantries
- Always end with the action taken or next step
- Preserve product names and model numbers exactly as spoken
- Do not use bullet points"""


def build_prompt(transcript: str, examples: list[dict]) -> str:
    """
    examples: list of {"transcript": str, "rep_note": str}
    """
    examples_block = ""
    if examples:
        examples_block = "\n\nHere are examples of good CRM notes in the correct style:\n"
        for i, ex in enumerate(examples, 1):
            examples_block += f"""
--- Example {i} ---
Transcript:
{ex['transcript']}

Note:
{ex['rep_note']}
"""

    return (
        f"<|begin_of_text|>"
        f"<|start_header_id|>system<|end_header_id|>\n\n"
        f"{SYSTEM_PROMPT}"
        f"{examples_block}"
        f"<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"Write a CRM note for this call transcript:\n\n{transcript}"
        f"<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
    )
```

### SummarizationThread

```python
class SummarizationThread(QThread):
    token_ready            = pyqtSignal(str)   # Each streamed token chunk
    summarization_complete = pyqtSignal(str)   # Full final text
    summarization_error    = pyqtSignal(str)   # Error message

    def __init__(self, llm, transcript, training_store):
        super().__init__()
        self.llm           = llm
        self.transcript    = transcript
        self.training_store = training_store
        self._cancelled    = False

    def run(self):
        try:
            examples = self.training_store.get_examples_for_prompt()
            prompt   = build_prompt(self.transcript, examples)
            full_text = ""

            for token in self.llm.create_completion(
                prompt,
                max_tokens=350,
                temperature=0.3,
                stream=True,
                stop=["<|eot_id|>", "<|end_of_text|>"]
            ):
                if self._cancelled:
                    break
                chunk = token['choices'][0]['text']
                full_text += chunk
                self.token_ready.emit(chunk)

            self.summarization_complete.emit(full_text.strip())

        except Exception as e:
            self.summarization_error.emit(str(e))

    def cancel(self):
        self._cancelled = True
```

**Streaming display:** Connect `token_ready` to a slot that appends the chunk
to the summary QTextEdit. This creates the real-time word-by-word streaming
effect. Do not clear and rewrite — only append.

---

## TRAINING DATA SYSTEM

### JSON Schema

```json
{
  "version": "1.0",
  "username": "ben.vitek",
  "examples": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2026-06-11T09:30:00",
      "transcript": "You: Hey John...\n\nCustomer: Yeah...",
      "ai_note": "called to follow up on quote...",
      "rep_note": "called john at acme...",
      "used_for_training": true
    }
  ]
}
```

### training_store.py

```python
class TrainingStore:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if os.path.exists(TRAINING_FILE):
            with open(TRAINING_FILE, 'r') as f:
                return json.load(f)
        return {"version": "1.0", "username": USERNAME, "examples": []}

    def save_example(self, transcript: str, ai_note: str, rep_note: str):
        example = {
            "id":               str(uuid.uuid4()),
            "timestamp":        datetime.now().isoformat(),
            "transcript":       transcript,
            "ai_note":          ai_note,
            "rep_note":         rep_note,
            "used_for_training": True
        }
        self.data['examples'].append(example)
        self._write()

    def get_examples_for_prompt(self) -> list[dict]:
        """Return the right number of examples based on how many are saved."""
        examples = self.data['examples']
        n = len(examples)
        if n == 0:
            return []
        elif n <= 5:
            selected = examples
        elif n <= 15:
            selected = examples[-7:]
        else:
            selected = examples[-10:]
        return [{"transcript": e["transcript"], "rep_note": e["rep_note"]}
                for e in selected]

    def _write(self):
        os.makedirs(TRAINING_DIR, exist_ok=True)
        with open(TRAINING_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)
```

### Save Trigger Rules

- **Save button in My Notes panel:** Save immediately when clicked. Show
  "Saved ✓" feedback on the button for 2 seconds, then restore "Save" label.
  Only available when My Notes has text.

- **Delete button:** Check if My Notes has text AND has NOT been saved this
  session. If both true, save training data automatically before clearing.
  Track this with a `self._training_saved_this_session` boolean flag, reset
  on every new recording start.

---

## CONFIG SYSTEM

### config.json Schema

```json
{
  "version": "1.0",
  "window": {
    "x": 1200,
    "y": 400,
    "width": 900,
    "height": 500
  },
  "app": {
    "app_version": "1.0.0",
    "last_update_check": "2026-06-11T09:00:00"
  }
}
```

### config_store.py

```python
DEFAULTS = {
    "version": "1.0",
    "window": {"x": None, "y": None, "width": 900, "height": 500},
    "app":    {"app_version": "1.0.0", "last_update_check": None}
}

class ConfigStore:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return copy.deepcopy(DEFAULTS)

    def save_window_geometry(self, x, y, width, height):
        self.data['window'].update({'x': x, 'y': y,
                                    'width': width, 'height': height})
        self._write()

    def get_window_geometry(self):
        return self.data.get('window', DEFAULTS['window'])

    def _write(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)
```

**On startup, validate saved window position:**
```python
geom = config.get_window_geometry()
screen = QApplication.primaryScreen().availableGeometry()
x = geom.get('x')
y = geom.get('y')
# If position is off-screen or None, use default bottom-right
if x is None or y is None or x < 0 or y < 0 or \
   x > screen.width() or y > screen.height():
    x = screen.right() - geom['width'] - 20
    y = screen.bottom() - geom['height'] - 20
panel.setGeometry(x, y, geom['width'], geom['height'])
```

---

## ERROR HANDLING — COMPLETE RULES

All errors display INSIDE the panel. Never use blocking QMessageBox except
for the close-while-recording warning.

| Scenario | What to show | Where |
|----------|-------------|-------|
| No microphone found at startup | "No microphone detected. Check audio settings." | Status bar, record button disabled |
| No loopback device | Persistent yellow warning banner below top bar: "Customer audio not detected — recording your mic only." | Below top bar, stays visible all session |
| Audio device disconnects mid-recording | Auto-stop, "Recording stopped: audio device disconnected." | Status bar |
| Recording stopped, no audio data | "No audio captured. Please try again." | Status bar, return to IDLE |
| Transcript is empty after processing | "No speech detected in recording." | Transcript panel |
| Transcript under 10 words total | Show transcript but add note: "Note: transcript is very short." | Below transcript |
| LLM fails before any output | "Summary generation failed. [Retry]" | Summary panel |
| LLM fails mid-generation | Keep partial text + append "\n\n⚠️ Generation stopped unexpectedly. Partial summary above. [Retry]" | Appended to summary panel |
| Model file missing at startup | Modal dialog: "AI model file not found. Please reinstall the application." App continues without summarization. | Dialog on startup |
| 1 hour of recording | Non-blocking inline prompt in status: "Recording for 1 hour — still recording? [Yes, continue] [Stop]" | Status bar area |
| 2 hours of recording | Auto-stop, show in status: "Recording auto-stopped at 2 hours." | Status bar |
| GitHub API unreachable | Silently skip, log to file | Log only |
| Config file corrupt | Delete and recreate with defaults. Log warning. | Log |
| Training file corrupt | Back up corrupt file as .bak, start fresh. Log warning. | Log |
| Close during recording | Modal dialog: "Recording in progress. Stop recording before closing?" [Keep Recording] [Stop and Close] | Dialog |

**Retry button behavior:** Clicking [Retry] in the summary panel restarts
SummarizationThread with the same transcript already in memory. Clear the
summary panel text first, then stream the new response.

---

## UPDATE CHECKER

```python
import requests
from version import APP_VERSION, GITHUB_REPO

class UpdateCheckThread(QThread):
    update_available = pyqtSignal(str)   # latest version string

    def run(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            latest = data['tag_name'].lstrip('v')
            if self._is_newer(latest, APP_VERSION):
                self.update_available.emit(latest)
        except Exception as e:
            # Silent fail — update check is non-critical
            logger.debug(f"Update check failed: {e}")

    def _is_newer(self, latest: str, current: str) -> bool:
        """Compare version strings e.g. '1.2.0' > '1.1.0'"""
        try:
            l = tuple(int(x) for x in latest.split('.'))
            c = tuple(int(x) for x in current.split('.'))
            return l > c
        except Exception:
            return False
```

**When update found — show banner below top bar:**
```
Background: rgba(48, 209, 88, 0.15)
Border:     1px rgba(48, 209, 88, 0.30)
Text:       "Version {latest} available  [Download Update]"
Text color: #30D158

[Download Update] button opens:
webbrowser.open(f"https://github.com/{GITHUB_REPO}/releases/latest")
```

### version.py
```python
APP_VERSION  = "1.0.0"
GITHUB_REPO  = "your-github-username/call-note-recorder"
```

Replace `your-github-username` with Ben's actual GitHub username when the
repo is created.

---

## QTHREAD SIGNAL ARCHITECTURE

All background work runs in QThread subclasses. The main thread handles UI
only. Never call UI methods from a non-main thread — always use signals.

### Thread → UI signal connections:

```python
# In main_window.py — wire everything up here

# Model loader
model_loader.models_ready.connect(self.on_models_ready)
model_loader.progress.connect(self.status_bar.setText)

# Recording
recording_thread.stopped_signal.connect(self.on_recording_stopped)
recording_thread.error_signal.connect(self.on_recording_error)

# Transcription
transcription_thread.segment_ready.connect(self.on_segment_ready)
transcription_thread.progress_update.connect(self.status_bar.setText)
transcription_thread.transcription_complete.connect(self.on_transcription_complete)
transcription_thread.error_signal.connect(self.on_transcription_error)

# Summarization
summarization_thread.token_ready.connect(self.on_token_ready)
summarization_thread.summarization_complete.connect(self.on_summarization_complete)
summarization_thread.summarization_error.connect(self.on_summarization_error)

# Update checker
update_thread.update_available.connect(self.on_update_available)
```

### on_segment_ready(speaker, text):
```python
def on_segment_ready(self, speaker: str, text: str):
    # Append to transcript panel
    color = "#AADDFF" if speaker == "You" else "#FFDDAA"
    self.transcript_panel.append(
        f'<span style="color:{color};font-weight:bold">{speaker}:</span> {text}<br><br>'
    )
```

### on_token_ready(chunk):
```python
def on_token_ready(self, chunk: str):
    # Append raw text — no HTML — to summary panel
    cursor = self.summary_edit.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    cursor.insertText(chunk)
    self.summary_edit.setTextCursor(cursor)
    self.summary_edit.ensureCursorVisible()
```

---

## RECORDING TIMER

```python
self._record_start_time = None
self._timer = QTimer()
self._timer.timeout.connect(self._tick)

def start_timer(self):
    self._record_start_time = time.time()
    self._timer.start(1000)

def stop_timer(self):
    self._timer.stop()
    self._record_start_time = None
    self.timer_label.setText("00:00")

def _tick(self):
    if not self._record_start_time:
        return
    elapsed = int(time.time() - self._record_start_time)
    m, s = divmod(elapsed, 60)
    self.timer_label.setText(f"{m:02d}:{s:02d}")

    if elapsed == 3600:       # 1 hour exactly
        self._show_one_hour_warning()
    elif elapsed >= 7200:     # 2 hours
        self.stop_recording()
        self.status_label.setText("Auto-stopped at 2 hours")
```

---

## LOGGING SETUP

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = os.path.join(LOGS_DIR, 'app.log')

    handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=3
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s: %(message)s'
    ))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.addHandler(logging.StreamHandler())  # Also print to console
```

---

## COMPLETE CONTROL BEHAVIOR REFERENCE

| Control | State it appears | Action |
|---------|-----------------|--------|
| Record button (grey ●) | IDLE | Start recording → state RECORDING |
| Stop button (red ■) | RECORDING | Stop recording → state TRANSCRIBING |
| Timer | RECORDING | Display elapsed MM:SS |
| Status bar | All | Show current state text |
| [─] Minimize | TRANSCRIBING, SUMMARIZING, COMPLETE | Collapse panel to icon widget. Data preserved in memory. |
| [✕] Close | All | If RECORDING: warning dialog. Otherwise hide to tray. |
| Tray → Show/Hide | All | Toggle panel/icon visibility |
| Tray → Quit | All | If RECORDING: warning dialog. Otherwise full quit. |
| [Delete] button | COMPLETE only | Check unsaved My Notes → auto-save if needed → clear all → state IDLE → show icon only |
| [Copy] (Transcript) | TRANSCRIBING, COMPLETE | Copy transcript text to clipboard |
| [Copy] (Summary) | SUMMARIZING, COMPLETE | Copy summary text to clipboard |
| [Copy] (My Notes) | COMPLETE | Copy My Notes text to clipboard |
| [Save] (My Notes) | COMPLETE | Save training example → show "Saved ✓" 2 sec → restore button |
| [Retry] (Summary) | COMPLETE after error | Clear summary panel → restart SummarizationThread |
| Column header [▾] | TRANSCRIBING, COMPLETE | Collapse/expand that column |
| Record button | COMPLETE | Auto-clear session → state IDLE → immediately → state RECORDING |
| [Download Update] | Any (when banner shown) | Open GitHub releases page in default browser |

---

## CORPORATE ENVIRONMENT — IMPLEMENTATION RULES

1. **Never hardcode any path.** All paths in utils/paths.py only.

2. **All app storage in %APPDATA%\CallNoteRecorder\.** No exceptions.

3. **No registry writes except the one-time Long Paths enable** (handled by
   installer, not the app itself).

4. **No system services.** App runs only when user opens it.

5. **GitHub API calls use requests** (pip-system-certs is installed and
   patches certifi to trust the Windows cert store automatically).

6. **Runtime HTTPS:** Import pip_system_certs at app startup:
   ```python
   try:
       import pip_system_certs.wrapt_requests
   except ImportError:
       pass  # Non-critical — will still work on non-Zscaler machines
   ```

7. **Domain machine:** Do not require elevation at runtime. All operations
   must work as a standard domain user.

8. **OneDrive Desktop:** Never write shortcuts or files to the Desktop path.
   Installer creates Start Menu shortcut only.

---

## WHAT THE INSTALLER MUST DO (for reference — not the app itself)

The installer (NSIS or Inno Setup) must:
1. Bundle Python 3.11.9 portable or use existing system Python
2. Bundle all .whl files — do NOT run live pip downloads
3. Run the llama-cpp-python source build with CMAKE_ARGS set
4. Enable Windows Long Paths via registry (requires admin, installer runs as admin)
5. Add torch/lib to user PATH
6. Create %APPDATA%\CallNoteRecorder\ folder structure
7. Bundle Llama 3.2 3B GGUF model OR download it on first run
8. Create Start Menu shortcut
9. Be re-runnable (repair installs)

---

## DEVELOPMENT NOTES FOR CLAUDE CODE

- **Test environment is Windows only.** This app uses Win32 DWM API and
  pyaudiowpatch WASAPI — it will not run on Mac or Linux. Develop the logic,
  then test on the Windows machine.

- **Pre-flight script** at `preflight.py` (on Windows Desktop) verifies all
  dependencies before each dev session. Run it and confirm 10/10 PASS.
  Command: `python "%USERPROFILE%\OneDrive - KEYENCE\Desktop\preflight.py"`

- **Model path on target machine:**
  `C:\Users\ben.vitek\AppData\Roaming\CallNoteRecorder\models\Llama-3.2-3B-Instruct-Q4_K_M.gguf`

- **When creating GitHub repo:** Replace `your-github-username` in version.py
  with Ben's actual GitHub username.

- **Build incrementally:**
  1. First: get the icon widget showing and recording working
  2. Second: add transcription pipeline
  3. Third: add panel widget and LLM summarization
  4. Fourth: add training data save/load
  5. Fifth: add system tray, update checker, config persistence
  6. Last: polish UI styling and error handling

- **The note quality is entirely dependent on the prompt.** If notes don't
  match Ben's style, the prompt is the first thing to tune — not the model.

---

*Spec version: 1.0 | Ready for Claude Code implementation*
*All requirements locked | Pre-flight: 10/10 PASS on KAVITEKB*