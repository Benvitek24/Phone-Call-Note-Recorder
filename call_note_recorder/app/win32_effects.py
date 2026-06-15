"""Windows 11 Acrylic blur via the DWM API (ctypes).

Applied after a window is shown. Fails silently on older Windows / non-Windows
(the semi-transparent Qt background still looks fine).
"""

import ctypes

from utils.logger import get_logger

log = get_logger("win32")

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMSBT_ACRYLIC = 3


def apply_acrylic(hwnd: int):
    """Apply Windows 11 Acrylic backdrop behind the given window handle."""
    try:
        dwmapi = ctypes.windll.dwmapi  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return  # not on Windows / DWM unavailable

    try:
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(1)),
            ctypes.sizeof(ctypes.c_int),
        )
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(ctypes.c_int(DWMSBT_ACRYLIC)),
            ctypes.sizeof(ctypes.c_int),
        )
    except Exception as e:  # noqa: BLE001
        log.debug("Acrylic not applied: %s", e)
