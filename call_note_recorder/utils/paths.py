"""Single source of truth for every filesystem path the app uses.

CRITICAL RULE (from the spec): no path is ever hardcoded anywhere else in the
codebase. All storage lives under %APPDATA%\\CallNoteRecorder on Windows.

The APPDATA lookup has a non-Windows fallback purely so the modules can be
imported / syntax-checked on a Mac during development. On the target Windows
machine os.environ['APPDATA'] always exists, so behavior there is unchanged.
"""

import os

# On Windows APPDATA is always set. The fallback only matters for dev machines.
_APPDATA = os.environ.get('APPDATA') or os.path.join(
    os.path.expanduser('~'), 'AppData', 'Roaming'
)

APPDATA_BASE  = os.path.join(_APPDATA, 'CallNoteRecorder')
MODELS_DIR    = os.path.join(APPDATA_BASE, 'models')
TRAINING_DIR  = os.path.join(APPDATA_BASE, 'training_data')
LOGS_DIR      = os.path.join(APPDATA_BASE, 'logs')
TEMP_DIR      = os.path.join(APPDATA_BASE, 'temp')

CONFIG_FILE   = os.path.join(APPDATA_BASE, 'config.json')
MODEL_FILE    = os.path.join(MODELS_DIR, 'Llama-3.2-3B-Instruct-Q4_K_M.gguf')

MIC_WAV       = os.path.join(TEMP_DIR, 'mic.wav')
LOOPBACK_WAV  = os.path.join(TEMP_DIR, 'loopback.wav')

USERNAME      = os.environ.get('USERNAME') or os.environ.get('USER', 'default')
TRAINING_FILE = os.path.join(TRAINING_DIR, f'{USERNAME}.json')

# Tray / window icon. Falls back gracefully if the asset is missing.
ASSETS_DIR    = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
TRAY_ICON     = os.path.join(ASSETS_DIR, 'tray.png')


def ensure_dirs():
    """Create all runtime storage directories. Safe to call repeatedly."""
    for d in (MODELS_DIR, TRAINING_DIR, LOGS_DIR, TEMP_DIR):
        os.makedirs(d, exist_ok=True)
