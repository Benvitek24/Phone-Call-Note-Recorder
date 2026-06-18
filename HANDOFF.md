# Call Note Recorder — Session Handoff

**Last updated: 2026-06-18** · For: a fresh Claude Code session picking up this project.

---

## How to use this doc
Read this first, then `Claude_Code_Spec.md` (the build spec) and `Project (10).md`
(the "why" / locked decisions + v1 failure lessons). This file is the current
state of reality; the spec is the original plan. Where they differ, this file wins.

**Start with the OPEN ISSUES section near the bottom — that's the active work.**

---

## Project in one paragraph
A local, offline Windows desktop app (PyQt6) for Keyence inside sales reps. It
records Microsoft Teams calls capturing the rep's mic and the system loopback as
**separate** streams (mic = "You", loopback = "Customer"), transcribes both with
faster-whisper (GPU), and writes a paste-ready CRM note with a local llama-cpp LLM
(CPU). A per-user few-shot training loop (My Notes → Save) improves note style.
Fully local: no cloud, no API, no background service. Target: 80→hundreds of reps.

## Who the user is
**Ben Vitek** (GitHub `Benvitek24`), Keyence inside sales rep, **not a developer**
(explain without jargon; he can run commands and follow steps). Strong opinions on
UI quality. Priority: **usability and correct transcripts/notes** — he considers
summarization quality already good enough, so do NOT over-invest in prompt wording
beyond fixing correctness bugs.

## Dev workflow & environment (IMPORTANT)
- Ben develops on a **personal macOS laptop** (this session) and deploys to his
  **Windows work PC** (no Claude Code there). **GitHub is the bridge.**
- Repo: **https://github.com/Benvitek24/Phone-Call-Note-Recorder** (public).
  Local Mac path: `/Users/benvitek/Documents/Projects/Phone Call Note Recorder/`
  (git root; app source under `call_note_recorder/`). Push credential is in the
  Mac keychain (a fine-grained PAT — may expire; re-issue if push fails).
- **The app CANNOT run or be tested on the Mac** — it needs Win32 DWM (Acrylic),
  pyaudiowpatch WASAPI loopback, and CUDA faster-whisper. Only pure-Python modules
  import on Mac. Workflow each change: edit on Mac → `git push` → Ben does
  `git pull` + `python main.py` on Windows → he pastes terminal output / transcripts
  back. You diagnose from that. `py_compile` + stubbed-PyQt unit tests are the only
  local verification available.
- Windows run: `cd %USERPROFILE%\Phone-Call-Note-Recorder\call_note_recorder` then
  `python main.py` (or double-click `launch.bat`; desktop shortcut exists).

## Windows environment facts
- i9-12950HX (Alder Lake, **no AVX-512**) → `llama-cpp-python` MUST be built from
  source with the CMAKE flags in the spec (prebuilt wheels crash 0xc000001d).
- LLM runs CPU only (`n_gpu_layers=0`), Whisper on CUDA. Model at
  `%APPDATA%\CallNoteRecorder\models\Llama-3.2-3B-Instruct-Q4_K_M.gguf`.
- All runtime data in `%APPDATA%\CallNoteRecorder\` (models, training_data, logs,
  temp, config.json). Training data is per-Windows-user and gitignored — you cannot
  see it from the Mac; ask Ben to paste `training_data\<USER>.json` or the transcript.
- Logs: `%APPDATA%\CallNoteRecorder\logs\app.log`.

---

## Architecture map (`call_note_recorder/`)
- `main.py` — startup sequence, QApplication, tray.
- `app/main_window.py` — `AppController`: state machine (IDLE→RECORDING→
  TRANSCRIBING→SUMMARIZING→COMPLETE) + all QThread signal wiring. Owns icon+panel.
- `app/icon_widget.py` — floating always-on-top record button.
- `app/panel_widget.py` — 3-column panel (Transcript | Summary | My Notes),
  drag/resize/collapse, CRM "Copy header" field, banners.
- `app/device_dialog.py` — audio device picker dialog.
- `app/tray_manager.py`, `app/styles.py`, `app/win32_effects.py` (Acrylic).
- `core/audio_recorder.py` — dual-stream WASAPI capture, device enum/select,
  silence-padding alignment, mono downmix.
- `core/transcription.py` — faster-whisper, **word-level** timestamp merge,
  **bleed suppression**, transcript-length cap for the LLM.
- `core/llm_engine.py` — llama-cpp prompt builder + streaming summarization.
- `core/model_loader.py` — loads Whisper (offline-first) + LLM at startup.
- `core/update_checker.py` — GitHub Releases check.
- `data/config_store.py` — config.json (window geom, crm_header, device prefs).
- `data/training_store.py` — per-user few-shot examples (ramp 0/≤5/≤15/15+).
- `utils/paths.py` (every path), `utils/logger.py`.

## What works (verified on Windows)
Record → transcribe (GPU) → summarize (CPU) → 3-column panel with streamed note;
training save/load; long calls (~8 min); auto-clear + empty-clip edge case;
always-on-top larger icon; editable transcript/summary; CRM copy-header; device
picker lists hardware; stream alignment (durations match); dedupe on Save.

## Fixed this session (newest first)
- Cross-hardware audio: **device picker** (⚙ Devices / tray) + **bleed suppression**
  (drop mic words duplicating a loopback word within ~1s; loopback is always clean
  customer). Mic-only recordings unaffected.
- **Word-level timestamp merge** for better ordering on overlapping speech.
- Day-1 usability: always-on-top + bigger icon, editable transcript/summary,
  auto-focus + styled My Notes, stronger Save confirmation w/ count, CRM header.
- Offline-first Whisper load (no HuggingFace ping each startup); quieted noisy libs;
  dedupe repeated Save.
- Earlier: fixed Stop-hang on silent loopback (poll get_read_available +
  resample_poly); silence-padding to keep streams real-time aligned; 8 spec-review
  corrections (tagged A–H in code: merged mouseMoveEvent, tray controller ref,
  loopback mono downmix, n_ctx=8192, budgeted few-shot, ordered transcript,
  1h-warning guard, no double-BOS).

---

## OPEN ISSUES — start here

### 1. (NEW, HIGH) Summary pulls in content from saved training examples
Symptom (2026-06-18): a generated note mixed content from a *previously saved
example* with the current call, producing an off-topic summary.
- **Likely cause:** few-shot contamination. `core/llm_engine.py build_prompt()`
  injects past example **transcripts** (`get_examples_for_prompt()` returns
  transcript+rep_note). A 3B model copies from them, worsened by topically-similar
  calls (all about 3D scanners).
- **Suggested fixes to try (in order):**
  1. Feed past **rep_notes only** as *style* samples, WITHOUT their transcripts —
     removes other-call content the model can copy. (Edit `build_prompt` + maybe
     `TrainingStore.get_examples_for_prompt`.)
  2. Strengthen the instruction: clearly fence the current transcript and say
     "summarize ONLY the transcript below; the examples are for writing STYLE only."
  3. Consider `create_chat_completion` with examples as prior user/assistant turns
     so the final user turn is unambiguously the task.
  4. Keep temperature 0.3; reduce example count if needed.
- Get Ben to paste the offending transcript + resulting summary + his
  `training_data\<USER>.json` to confirm which example bled in.

### 2. (PENDING VALIDATION) Bleed suppression + device picker
Just shipped; needs Ben to test on (a) the bad "Jack Mic"/speaker setup — confirm
duplication is cleaned — and (b) after picking "Microphone Array" + "Headphones".
Watch the `Bleed suppression: kept X/Y mic words` log line. Tune the ~1s match
window or text-normalization if real overlap is over- or under-suppressed.
Background: loopback is ALWAYS clean customer; only the mic bleeds (acoustic on open
speakers, electrical "Jack Mic" crosstalk with plain aux in a combo jack). A proper
USB/Bluetooth headset is the clean hardware path for rollout.

### 3. (DEPRIORITIZED) Note-style tuning to Ben's voice
His real note style sample is in `Project (10).md` Section 5 (lowercase, terse,
third-person about customer, "i" for self, ends with the action e.g. "sending ILS
and inputting lead"). He's happy with current quality, so only touch the prompt for
correctness (see issue #1), not style polish, unless he asks.

### 4. (MINOR / polish)
- 1-hour warning is text-only; spec wanted interactive [Yes][Stop].
- Old QThreads not explicitly released (slight leak over a heavy day).
- Eventually swap `launch.bat` for a no-console (pythonw) launcher once stable.
- Acrylic blur look unverified; resize/drag/column-collapse unverified by Ben.
- `version.py GITHUB_REPO` is set; no GitHub Releases cut yet (updater is dormant).

---

## Hard constraints (do not break)
PyQt6 only; llama-cpp-python (CPU, source build); never mix mic+loopback before
transcription; no hardcoded paths (all in `utils/paths.py`); no background service;
no animation; offline after setup. See `Claude_Code_Spec.md` "CRITICAL CONSTRAINTS".

## Pointers
- Spec: `Claude_Code_Spec.md`. History/decisions: `Project (10).md`.
- Auto-memory (loads each session on this Mac): `user-ben-vitek`,
  `project-call-note-recorder`.
- Security: PATs Ben pasted earlier are in the old transcript — they should be
  revoked at https://github.com/settings/tokens; re-issue when a push is needed.
