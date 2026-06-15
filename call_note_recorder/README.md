# Call Note Recorder

Local Windows desktop app for Keyence inside sales reps. Records Microsoft Teams
calls (mic + WASAPI loopback, kept separate), transcribes both sides with speaker
labels, and writes a paste-ready CRM note with a local LLM — fully offline, no
cloud, no subscriptions, no background services.

Built from `Claude_Code_Spec.md`. Develop on Mac → push to GitHub → pull and run
on the Windows machine. **This app only runs on Windows** (Win32 DWM Acrylic,
pyaudiowpatch WASAPI loopback, CUDA faster-whisper).

---

## Quick start (Windows target machine)

1. **Clone / pull the repo.**
2. **Confirm the environment** with the pre-flight script (expects `10/10`):
   ```
   python "%USERPROFILE%\OneDrive - KEYENCE\Desktop\preflight.py"
   ```
3. **Place the model** at:
   ```
   %APPDATA%\CallNoteRecorder\models\Llama-3.2-3B-Instruct-Q4_K_M.gguf
   ```
4. **Run:**
   ```
   cd call_note_recorder
   python main.py
   ```

## First-time package setup (Windows)

```
python -m pip install -r requirements.txt
```

### LLM build — CRITICAL (12th Gen Intel / Alder Lake has no AVX-512)

Pre-built `llama-cpp-python` wheels crash with `0xc000001d`. It must be built
from source:

```
:: 1. Long paths (run as admin, one time)
reg add "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1 /f

:: 2. VS Build Tools 2022 with the C++ workload must be installed

:: 3. Build from source (CPU only — intentional)
set CMAKE_ARGS=-DGGML_AVX512=OFF -DGGML_AVX512_VBMI=OFF -DGGML_AVX512_VNNI=OFF -DGGML_AMX_TILE=OFF -DGGML_AMX_INT8=OFF -DGGML_AMX_BF16=OFF -DGGML_AVX2=ON -DGGML_AVX=ON -DGGML_FMA=ON
python -m pip install llama-cpp-python --no-binary llama-cpp-python
```

`torch\lib` must be on PATH for the llama DLL to load (already permanent on the
target machine; the installer handles it elsewhere).

---

## Project structure

```
call_note_recorder/
├── main.py                 entry point + startup sequence
├── version.py              APP_VERSION, GITHUB_REPO  (set the repo before release)
├── app/
│   ├── main_window.py      AppController — state machine + all signal wiring
│   ├── icon_widget.py      floating record button
│   ├── panel_widget.py     3-column panel (drag/resize/collapse)
│   ├── tray_manager.py     system tray
│   ├── win32_effects.py    Acrylic blur (DWM)
│   └── styles.py           all QSS
├── core/
│   ├── audio_recorder.py   dual-stream WASAPI capture
│   ├── transcription.py    faster-whisper pipeline + merge
│   ├── llm_engine.py       llama-cpp prompt + streaming
│   ├── model_loader.py     loads Whisper + LLM at startup
│   └── update_checker.py   GitHub Releases check
├── data/
│   ├── config_store.py     window geometry / config.json
│   └── training_store.py   per-user few-shot examples
└── utils/
    ├── paths.py            every path (nothing hardcoded elsewhere)
    └── logger.py           rotating file log
```

Runtime data lives entirely in `%APPDATA%\CallNoteRecorder\`.

---

## Corrections applied on top of spec v1.0

These were fixed while building so they don't cost a Mac→Windows round-trip.
See inline comments tagged with the review item letter.

- **A** — Panel had two `mouseMoveEvent` defs (drag + resize); merged into one so
  drag-to-move works.
- **B** — `TrayManager` now stores `self.app_controller` (double-click no longer
  crashes).
- **C** — Loopback opens at its real channel count and is **downmixed to mono**
  on save (mono-only open usually fails for stereo loopback).
- **D** — `n_ctx` raised to **8192**; transcript is size-capped before the LLM so
  a long (up to ~50 min) call fits.
- **E** — Training examples are stored in full but packed into the prompt as
  **short excerpts** under a budget, so the context never overflows.
- **F** — Live transcript streams for feedback, then is **replaced by the
  time-ordered merged transcript** (no jarring reshuffle).
- **G** — 1-hour warning uses `>=` + a guard flag (a dropped timer tick can't
  skip it). 2-hour auto-stop unchanged.
- **H** — Removed the literal `<|begin_of_text|>` to avoid a double-BOS token.

Plus: graceful "No microphone detected" / "No audio captured" paths, and
mid-recording device-disconnect handling.

---

## Before first GitHub release

In `version.py`, set:

```python
GITHUB_REPO = "<your-github-username>/call-note-recorder"
```

The in-app update checker reads it.
