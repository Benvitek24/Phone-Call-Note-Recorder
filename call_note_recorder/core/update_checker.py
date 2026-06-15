"""GitHub Releases update check. Silent on failure (non-critical)."""

import requests

from PyQt6.QtCore import QThread, pyqtSignal

from version import APP_VERSION, GITHUB_REPO
from utils.logger import get_logger

log = get_logger("update")


class UpdateCheckThread(QThread):
    update_available = pyqtSignal(str)  # latest version string

    def run(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            latest = str(resp.json()['tag_name']).lstrip('v')
            if self._is_newer(latest, APP_VERSION):
                self.update_available.emit(latest)
        except Exception as e:  # noqa: BLE001 - update check must never crash app
            log.debug("Update check failed: %s", e)

    @staticmethod
    def _is_newer(latest: str, current: str) -> bool:
        try:
            l = tuple(int(x) for x in latest.split('.'))
            c = tuple(int(x) for x in current.split('.'))
            return l > c
        except (ValueError, AttributeError):
            return False
