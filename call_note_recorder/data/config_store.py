"""Loads/saves config.json (window geometry, last update check).

Corrupt-config rule (spec Error Handling): if the file won't parse, log a
warning, recreate from defaults.
"""

import copy
import json

from utils.paths import CONFIG_FILE
from utils.logger import get_logger

log = get_logger("config")

DEFAULTS = {
    "version": "1.0",
    "window": {"x": None, "y": None, "width": 900, "height": 500},
    "app":    {"app_version": "1.0.0", "last_update_check": None},
    "crm_header": "SPT INTERNAL PROJECT",
    "devices": {"mic_name": None, "output_name": None},
}


class ConfigStore:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Merge onto defaults so missing keys are always present.
            merged = copy.deepcopy(DEFAULTS)
            merged.update({k: v for k, v in data.items() if k in merged})
            for section in ("window", "app", "devices"):
                if isinstance(data.get(section), dict):
                    merged[section] = {**DEFAULTS[section], **data[section]}
            return merged
        except FileNotFoundError:
            return copy.deepcopy(DEFAULTS)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("config.json unreadable (%s) — recreating from defaults", e)
            data = copy.deepcopy(DEFAULTS)
            try:
                self._write_data(data)
            except OSError:
                pass
            return data

    def save_window_geometry(self, x, y, width, height):
        self.data['window'].update(
            {'x': int(x), 'y': int(y), 'width': int(width), 'height': int(height)}
        )
        self._write()

    def get_window_geometry(self) -> dict:
        return self.data.get('window', DEFAULTS['window'])

    def set_last_update_check(self, iso_timestamp: str):
        self.data.setdefault('app', {})['last_update_check'] = iso_timestamp
        self._write()

    def get_crm_header(self) -> str:
        return self.data.get('crm_header', DEFAULTS['crm_header'])

    def set_crm_header(self, text: str):
        self.data['crm_header'] = text
        self._write()

    def get_device_prefs(self):
        """Return (mic_name, output_name); either may be None (= auto/default)."""
        d = self.data.get('devices', DEFAULTS['devices'])
        return d.get('mic_name'), d.get('output_name')

    def set_device_prefs(self, mic_name, output_name):
        self.data['devices'] = {'mic_name': mic_name, 'output_name': output_name}
        self._write()

    def _write(self):
        self._write_data(self.data)

    @staticmethod
    def _write_data(data):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
