# Call Note Recorder — Master Project Document
**Version: 5.0 — Claude Code Spec Complete**
**Last Updated: Session 3 final**

---

## ⚠️ INSTRUCTIONS FOR ALL AI ASSISTANTS — READ FIRST

This is the single source of truth for this project. It is a living document.

**AT THE END OF EVERY SESSION** — output the complete updated PROJECT.md in a
single 4-backtick code block so the user can copy the entire file and save it
as PROJECT.md. The user should never need to upload more than this one file to
continue work in a new session.

**DO NOT output partial updates.**
**DO NOT split the document across multiple code blocks.**
**DO NOT make the user ask for this — output it automatically at session end.**

---

## CURRENT STATUS AT A GLANCE

| Item | Status |
|------|--------|
| Requirements Sections 1-11 | ✅ FULLY LOCKED |
| Tech stack decision | ✅ FULLY LOCKED |
| GPU/CUDA setup | ✅ CONFIRMED WORKING |
| PyTorch CUDA build | ✅ INSTALLED — torch 2.5.1+cu121 |
| Pre-build checklist | ✅ COMPLETE — all items confirmed |
| Pre-flight check script | ✅ CREATED AND PASSED — 10/10 |
| Claude Code spec | ✅ PRODUCED — CLAUDE_CODE_SPEC.md |
| New build | ⏳ NOT STARTED — hand off to Claude Code |

**Next immediate action:** Give CLAUDE_CODE_SPEC.md to Claude Code and begin build.

---

## PRE-FLIGHT RESULTS (Last Run)

```
Machine : KAVITEKB
User    : Ben.Vitek
Python  : 3.11.9

RESULTS: 10 / 10 checks passed
GO -- All systems ready for Claude Code

Highlights:
  torch 2.5.1+cu121 | GPU: NVIDIA RTX A2000 8GB Laptop GPU
  faster-whisper loaded on GPU OK
  Loopbacks found: 4 (Zone Vibe 125 confirmed)
  Model found — 2.0 GB
  LLM output time: 0.9 seconds
  AppData: C:\Users\ben.vitek\AppData\Roaming\CallNoteRecorder
```

---

## WHO THIS IS FOR AND WHO BEN IS

**User:** Ben Vitek — Keyence inside sales representative
**Machine:** Dell Precision 7670 (KAVITEKB.keyence.com)
**OS:** Windows 11 Enterprise (Build 10.0.26200)
**CPU:** Intel i9-12950HX (12th Gen Alder Lake — NO AVX-512 support)
**RAM:** 64GB
**GPU:** NVIDIA RTX A2000 8GB Laptop — CUDA confirmed working ✅
**Driver:** 581.95 | CUDA Version: 13.0
**Storage:** 954GB (~538GB free)
**Domain:** keyence.com (corporate machine)
**Admin rights:** YES confirmed
**Desktop path:** C:\Users\ben.vitek\OneDrive - KEYENCE\Desktop
  ⚠️ NOT the standard Windows path — redirected to OneDrive by IT

**Ben's technical level:** Above average for a sales rep. Can run commands,
follow technical instructions, troubleshoot. Not a developer.

**Development workflow:** Ben develops on Mac using Claude Code, deploys to
Windows. GitHub is the bridge between the two machines.

**The problem being solved:**
Ben spends 10-15 minutes after every sales call manually typing notes into
Keyence's SFA CRM system. He makes many calls per day. The team is 80 people,
potentially growing to hundreds. Goal: record the call, transcribe with speaker
labels, generate a paste-ready CRM note automatically.

---

## PART 1 — THE FIRST ITERATION: WHAT WAS BUILT AND WHY IT FAILED

### What v1 Was
A Python desktop app using pywebview 4.4.1, openai-whisper (CPU only),
Ollama + llama3.2, pyaudiowpatch, ctypes Win32 DWM API. Three animated
window states. Launched via .bat file. Reached v4.3.1 before abandoned.

### Core Failures and Lessons Learned

#### Failure 1 — Wrong UI Framework
pywebview fights every window management requirement. Snap-back bug never
fixed. Re-entrant resize loop. 400ms JS polling for position.
**Lesson:** Use PyQt6 for any precise Windows window management.

#### Failure 2 — Ollama as a Separate Service
If Ollama wasn't running, summarization failed. Unacceptable for 80 reps.
**Lesson:** Use llama-cpp-python — runs inside the Python process.

#### Failure 3 — Audio Streams Mixed Before Transcription
Mixing mic + loopback destroyed speaker information.
**Lesson:** Never mix streams. Mic = You, loopback = Customer. Always separate.

#### Failure 4 — GPU Never Investigated
CPU-only PyTorch. RTX A2000 unused entire project.
**Lesson:** Always verify GPU. torch.__version__ showing "+cpu" is the tell.

#### Failure 5 — Zscaler SSL
Standard pip fails. Download .whl via Edge. Installer must bundle all packages.

#### Failure 6 — Overengineered Animation
Multiple sessions wasted on snap-back and resize bugs.
**Lesson:** Use instant state changes.

#### Failure 7 — Hardcoded Paths
**Lesson:** Always use %APPDATA%, never hardcode Desktop or user paths.

---

## PART 2 — THE NEW VISION

### What We Are Building
A local desktop application for Keyence inside sales representatives that:
1. Records Teams phone calls — both sides separately
2. Transcribes with speaker labels ("You" and "Customer")
3. Generates AI CRM notes automatically
4. Streams AI note generation word by word in real time
5. Includes per-user feedback loop to improve note quality
6. Installs via one-click installer for team deployment
7. Updates automatically via GitHub Releases

### Core Principles (Non-Negotiable)
- **Fully local** — no cloud, no internet after setup
- **Completely free** — no subscriptions, no API costs
- **Self-contained** — no separate services to manage
- **Team deployable** — one installer, any Keyence corporate Windows laptop
- **Speaker-separated** — "You" and "Customer" always clearly labeled
- **Non-blocking** — rep can use other apps while transcription runs
- **Usability first** — if it's not easy to use, reps won't use it

---

## PART 3 — LOCKED DECISIONS

### Section 1 — Context and Constraints ✅

| Topic | Decision |
|-------|----------|
| Primary user | Ben Vitek — sole user for development and testing |
| Target deployment | Team of 80, potentially hundreds across Keyence |
| Hardware assumption | Dell Precision 7670 spec or equivalent |
| GPU | NVIDIA RTX A2000 8GB — CUDA confirmed working |
| Cost | 100% free — fully local AI, no API calls ever |
| Deployment | GitHub Releases → download installer → one click |
| First-run setup | Automated model downloads acceptable (10-20 min) |
| IT involvement | None — must work without IT |
| LLM architecture | llama-cpp-python — self-contained, no separate service |

### Section 2 — Core Workflow ✅

**Complete user flow:**
```
1.  App icon in taskbar or on desktop
2.  Double-click → small glassmorphic floating button appears bottom-right
3.  Rep clicks play → recording starts IMMEDIATELY
4.  Button turns red + pulses
5.  Top bar shows live timer counting up + "Recording..." status
6.  Call ends → rep clicks red button to stop
7.  Transcription begins automatically (non-blocking)
8.  Status: "Transcribing..." with progress bar + estimated time
9.  Transcript segments appear in real time as Whisper processes them
10. Transcription complete → summarization begins automatically
11. Status: "Summarizing..."
12. Panel expands — grows UP and LEFT from bottom-right anchor
13. Three columns appear: Transcript | Summary | My Notes
14. AI summary streams word by word in real time (like ChatGPT)
15. Rep reads Summary:
      IF good → copies → pastes into SFA → clicks Delete
      IF not good → types version in My Notes → copies that
16. Delete clears UI, saves training data if My Notes used, returns to icon
17. App immediately ready for next call
18. Pressing Record while minimized auto-deletes previous session
19. At 1 hour → prompt: "Still recording?"
20. At 2 hours → auto-stop with notification
```

**Panel layout:**
```
┌─────────────────────────────────────────────────────────┐
│  [●/■]  |  00:00  |  Status message  | [Delete] [─][✕] │
├──────────────────┬─────────────────┬────────────────────┤
│  [Transcript ▾]  │  [Summary ▾]    │  [My Notes ▾]      │
│                  │                 │                    │
│  You: ...        │  AI-written     │  Rep types own     │
│  Customer: ...   │  CRM note       │  version here      │
│                  │  streams in     │                    │
│                  │  real time      │                    │
│  [Copy]          │  [Copy]         │  [Copy] [Save]     │
└──────────────────┴─────────────────┴────────────────────┘
```

### Section 3 — Audio Capture ✅

| Topic | Decision |
|-------|----------|
| Call platform | Microsoft Teams Phone exclusively |
| Speaker separation | Mic → "You" / WASAPI loopback → "Customer" |
| Streams | NEVER mixed — transcribed independently |
| Bluetooth | Accepted limitation — HFP lower quality. Inform team. |
| Device switch mid-recording | Stop immediately, show warning |
| No loopback detected | Record mic-only, show persistent warning |
| Language | English only |

### Section 4 — Transcription ✅

| Topic | Decision |
|-------|----------|
| Engine | faster-whisper with CUDA GPU acceleration |
| Model | Small to start — upgrade to medium if needed |
| Speaker separation | Dual-stream — mic = You, loopback = Customer |
| Real-time display | Segments appear progressively as processed |
| Editing | Fully editable before summarizing |
| Call length | 2 minutes minimum, 50 minutes maximum |

### Section 5 — AI Summary ✅

| Topic | Decision |
|-------|----------|
| Note style | Lowercase, conversational, third person, no padding |
| Note length | Short call = short note. Never pad. |
| Must capture | Why call happened, application, products, next step |
| Never include | Anything not in transcript |
| Generation display | Streams word by word in real time |
| Training mechanism | Few-shot prompting — per-user saved examples |
| Training trigger | Only when rep fills My Notes and clicks Save |
| Example ramp-up | 0: base only / 1-5: all / 6-15: recent 7 / 15+: recent 10 |
| Per-user | YES — training data never shared across reps |

**Ben's style standard:**
```
said he didn't remember looking into anything 3D scanning or profiling
related. didn't have a use for VR / VL

he is working on the mechanical side of a pin picking operation where i
believe they are researching our 3D bin picking technology. he didn't know
who from his company was researching it and wanted to get connected with
our rep for the bin picking

sending ILS and inputting lead
```

### Section 6 — User Interface ✅

| Topic | Decision |
|-------|----------|
| Visual style | Glassmorphic — iOS Control Center reference |
| Colors | Whites, greys, blacks, transparency — no Keyence branding |
| Background effect | Windows 11 Acrylic blur via Win32 DWM API |
| Corners | Rounded throughout |
| Panel width | Default ~40% screen width, resizable, hard cap 50% |
| Panel height | ~35% screen height, user resizable |
| Anchor | Bottom-right corner — panel grows up and left |

### Section 7 — Window Behavior ✅

| Topic | Decision |
|-------|----------|
| Resizable | YES — rep can drag edges freely |
| Minimum window size | 600×350px |
| System tray | YES — always present while app running |
| Always on top | YES — floats above ALL windows |
| When minimized | Returns to small floating icon |
| Position memory | Remembers position and size between sessions |

### Section 8 — Data and Storage ✅

| Topic | Decision |
|-------|----------|
| Audio files | Deleted after transcription |
| Transcript/Summary | Session memory only — not saved |
| Training data | %APPDATA%\CallNoteRecorder\training_data\[username].json |
| Multiple users | Per Windows user profile |

### Section 9 — Error Handling ✅

| Topic | Decision |
|-------|----------|
| Recording warning | Prompt at 1 hour |
| Recording auto-stop | Hard stop at 2 hours |
| Error display | Inside panel — not blocking dialogs |
| LLM failure — partial | Keep partial + append error + retry button |
| No audio captured | Show error, do not proceed |
| Error logging | Log to %APPDATA%\CallNoteRecorder\logs\ |

### Section 10 — Performance ✅

| Topic | Decision |
|-------|----------|
| Transcription | NON-BLOCKING — GPU via faster-whisper |
| LLM generation | CPU — confirmed 0.9 seconds on i9-12950HX |
| GPU for LLM | NOT needed — CPU is sufficient |

### Section 11 — Installer and Updates ✅

| Topic | Decision |
|-------|----------|
| Installer | One-click: NSIS or Inno Setup |
| Zscaler handling | All packages bundled — no live downloads |
| Updates | GitHub Releases — app checks on launch |
| Update check | pip-system-certs handles Zscaler SSL |
| Update download | Opens browser to GitHub releases page |
| GitHub management | Ben manages from Mac via Claude Code |

---

## PART 4 — PRE-BUILD CHECKLIST ✅ COMPLETE

- [x] GPU: NVIDIA RTX A2000 8GB, CUDA available: True
- [x] PyTorch: torch 2.5.1+cu121
- [x] faster-whisper 1.2.1 + GPU: CONFIRMED WORKING
- [x] llama-cpp-python 0.3.28: CONFIRMED (CPU, 0.9 sec)
- [x] Llama 3.2 3B Q4_K_M GGUF: Downloaded (2.0 GB)
      Path: %APPDATA%\CallNoteRecorder\models\Llama-3.2-3B-Instruct-Q4_K_M.gguf
- [x] pyaudiowpatch 0.2.12.8: Zone Vibe 125 [Loopback] detected
- [x] PyQt6 6.11.0: Window launched
- [x] pyperclip 1.11.0: Clipboard working
- [x] pip-system-certs 5.3: Installed
- [x] pip 26.1.2: Upgraded
- [x] VS Build Tools 2022: Installed (C++ workload)
- [x] Windows Long Paths: Enabled via registry
- [x] torch/lib PATH: Added permanently to user environment
- [x] AppData folders: Created and writable
- [x] Pre-flight script: 10/10 PASS — GO confirmed

---

## PART 5 — PRE-FLIGHT CHECK SCRIPT

**File:** preflight.py — saved on Ben's Desktop
**Run command:**
```
python "%USERPROFILE%\OneDrive - KEYENCE\Desktop\preflight.py"
```

Run before every Claude Code session. Expected: `GO -- All systems ready`

**Script source:**
```python
import sys
import os
import time

results = []

def check(name, fn):
    try:
        fn()
        results.append((name, True, None))
        print(f"  PASS  {name}")
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"  FAIL  {name}: {e}")

print()
print("=" * 55)
print("   CALL NOTE RECORDER -- PRE-FLIGHT CHECK")
print("=" * 55)
print(f"\n  Python : {sys.version.split()[0]}")
print(f"  Machine: {os.environ.get('COMPUTERNAME', 'unknown')}")
print(f"  User   : {os.environ.get('USERNAME', 'unknown')}\n")

print("[ 1 ] Core packages")

def test_pyqt6():
    from PyQt6.QtWidgets import QApplication
check("PyQt6", test_pyqt6)

def test_pyperclip():
    import pyperclip
    pyperclip.copy("preflight-ok")
check("pyperclip", test_pyperclip)

def test_pipcerts():
    import pip_system_certs
check("pip-system-certs", test_pipcerts)

def test_scipy():
    import scipy, numpy
check("scipy + numpy", test_scipy)

print("\n[ 2 ] Audio")

def test_audio():
    import pyaudiowpatch as pyaudio
    p = pyaudio.PyAudio()
    devices = [p.get_device_info_by_index(i)['name']
               for i in range(p.get_device_count())]
    loopbacks = [d for d in devices if 'Loopback' in d]
    p.terminate()
    if not loopbacks:
        raise Exception("No loopback devices found")
    print(f"         Loopbacks found: {len(loopbacks)}")
    for d in loopbacks:
        print(f"           - {d}")
check("pyaudiowpatch + loopback devices", test_audio)

print("\n[ 3 ] GPU and transcription")

def test_torch():
    import torch
    if not torch.cuda.is_available():
        raise Exception("CUDA not available")
    print(f"         torch {torch.__version__} | GPU: {torch.cuda.get_device_name(0)}")
check("PyTorch CUDA", test_torch)

def test_whisper():
    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cuda")
    print("         faster-whisper loaded on GPU OK")
check("faster-whisper GPU", test_whisper)

print("\n[ 4 ] LLM")

MODEL_PATH = os.path.join(
    os.environ['APPDATA'],
    'CallNoteRecorder', 'models',
    'Llama-3.2-3B-Instruct-Q4_K_M.gguf'
)

def test_model_exists():
    if not os.path.exists(MODEL_PATH):
        raise Exception(f"Model file missing at: {MODEL_PATH}")
    print(f"         Model found — {os.path.getsize(MODEL_PATH)/1e9:.1f} GB")
check("Llama model file", test_model_exists)

def test_llm():
    from llama_cpp import Llama
    m = Llama(model_path=MODEL_PATH, n_gpu_layers=0, n_ctx=512, verbose=False)
    start = time.time()
    r = m.create_completion("Say hi in five words.", max_tokens=20)
    elapsed = time.time() - start
    print(f"         Output : '{r['choices'][0]['text'].strip()}'")
    print(f"         Time   : {elapsed:.1f} seconds")
    if elapsed > 30:
        raise Exception(f"LLM too slow: {elapsed:.1f}s")
check("llama-cpp-python inference", test_llm)

print("\n[ 5 ] Storage")

def test_storage():
    base = os.path.join(os.environ['APPDATA'], 'CallNoteRecorder')
    for folder in ['models','training_data','logs','temp']:
        os.makedirs(os.path.join(base, folder), exist_ok=True)
    tmp = os.path.join(base, 'training_data', '_preflight_test.tmp')
    with open(tmp, 'w') as f: f.write('ok')
    os.remove(tmp)
    print(f"         AppData path: {base}")
check("AppData folders + write access", test_storage)

passed = sum(1 for _, ok, _ in results if ok)
total  = len(results)

print()
print("=" * 55)
print(f"\n  RESULTS: {passed} / {total} checks passed\n")
if passed == total:
    print("  GO -- All systems ready for Claude Code")
else:
    print("  NOT GO -- Fix failures before proceeding.")
    for name, ok, err in results:
        if not ok:
            print(f"  -> FAILED: {name}\n             {err}")
print()
print("=" * 55)
print()
```

---

## PART 6 — TECH STACK ✅ FULLY LOCKED

| Component | Tool | Version | Notes |
|-----------|------|---------|-------|
| UI Framework | PyQt6 | 6.11.0 | Native window events |
| Visual style | PyQt6 + Win32 DWM Acrylic | — | Windows 11 glassmorphic |
| Audio capture | pyaudiowpatch | 0.2.12.8 | WASAPI loopback confirmed |
| Transcription | faster-whisper | 1.2.1 | GPU confirmed |
| LLM | llama-cpp-python | 0.3.28 | CPU-only source build |
| LLM Model | Llama 3.2 3B Q4_K_M GGUF | — | 0.9 sec confirmed |
| Clipboard | pyperclip | 1.11.0 | Working |
| Audio processing | scipy + numpy | — | Resampling only, no mixing |
| Config/storage | JSON stdlib | — | No extra dependencies |
| Training data | JSON in %APPDATA% | — | Per-user |
| Threading | QThread + signals | — | Native Qt threading |
| Installer | NSIS or Inno Setup | — | One-click |
| Updates | GitHub Releases API | — | pip-system-certs for Zscaler |
| SSL fix | pip-system-certs | 5.3 | Windows cert store trust |

---

## PART 7 — CRITICAL ENVIRONMENT NOTES

**⚠️ llama-cpp-python MUST be built from source on 12th Gen Intel**
All pre-built wheels crash: `OSError: [WinError -1073741795] 0xc000001d`
Root cause: Alder Lake has NO AVX-512. All pre-built wheels compiled with it.

**Required build process:**
```
# 1. Enable long paths (run as Administrator)
reg add "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1 /f

# 2. Install VS Build Tools 2022 with C++ workload, restart
# https://aka.ms/vs/17/release/vs_BuildTools.exe

# 3. Build from source
set CMAKE_ARGS=-DGGML_AVX512=OFF -DGGML_AVX512_VBMI=OFF -DGGML_AVX512_VNNI=OFF -DGGML_AMX_TILE=OFF -DGGML_AMX_INT8=OFF -DGGML_AMX_BF16=OFF -DGGML_AVX2=ON -DGGML_AVX=ON -DGGML_FMA=ON
python -m pip install llama-cpp-python --no-binary llama-cpp-python
```

**LLM runs on CPU — intentional and confirmed sufficient**
0.9 seconds for output on i9-12950HX. GPU used only for faster-whisper.

**torch PATH required permanently:**
```
C:\Users\ben.vitek\AppData\Local\Programs\Python\Python311\Lib\site-packages\torch\lib
```

**Zscaler:** Use `python -m pip`. pip-system-certs handles runtime HTTPS.
Large packages: download via Edge, install .whl locally.

**OneDrive Desktop:** Never hardcode. Use %APPDATA% for all app storage.

**Audio devices on Ben's machine:**
- Mic: Headset Microphone (Zone Vibe 125) → "You"
- Loopback: Headset Earphone (Zone Vibe 125) [Loopback] → "Customer"

---

## PART 8 — INSTRUCTIONS FOR THE NEXT AI ASSISTANT

**Requirements: 100% locked. Pre-build: complete. Pre-flight: GO.**
**Claude Code spec: PRODUCED — use CLAUDE_CODE_SPEC.md for the build.**

**If continuing requirements or debugging:**
Read this entire document first. All decisions are locked — do not reopen them
without a strong reason and explicit discussion with Ben.

**If helping Ben with Claude Code:**
The CLAUDE_CODE_SPEC.md is the document to give Claude Code. Do not give it
this PROJECT.md — too much history. The spec has everything Claude Code needs.

**Key facts about Ben:**
- Not a developer — no jargon without explanation
- Strong opinions about UI quality — take them seriously
- Develops on Mac (Claude Code), deploys to Windows via GitHub
- End goal: 80-hundreds of Keyence reps
- LLM training feature is important to him personally
- Zone Vibe 125 headset is primary audio device

---

## SESSION LOG

### Session 1 — Initial Build
Built v1. Reached v4.3.1. Key failures: pywebview window bugs,
no speaker separation, GPU unused, Ollama dependency. Abandoned.

### Session 2 — Requirements Gathering
Full requirements Sections 1-11. CUDA confirmed. Zscaler documented.
New vision established. Tech stack decided.

### Session 3 — Finalization + Pre-Build + Pre-Flight + Spec
- Locked all open questions
- Ran complete pre-build checklist — all passing
- Discovered: 12th Gen Intel no AVX-512 — must build from source
- Discovered: LLM CPU = 0.9 sec — GPU not needed for LLM
- VS Build Tools 2022 installed, Windows Long Paths enabled
- Zone Vibe 125 confirmed with WASAPI loopback
- Created preflight.py — 10/10 PASS confirmed
- Produced CLAUDE_CODE_SPEC.md — ready for Claude Code

### Session 4 — [NEXT SESSION]
Begin build with Claude Code using CLAUDE_CODE_SPEC.md.
Run preflight.py first to confirm GO before starting.

---

*Document version: 5.0 | Session 3 complete — FULL GO |
Next action: Hand CLAUDE_CODE_SPEC.md to Claude Code and begin build*