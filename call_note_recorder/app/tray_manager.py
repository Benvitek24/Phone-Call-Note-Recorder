"""System tray icon and menu.

Correction folded in (review item B): the spec's _on_activated referenced
self.app_controller but __init__ never stored it -> AttributeError on
double-click. It is stored here.
"""

import os

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction, QIcon, QPixmap, QColor

from utils.paths import TRAY_ICON


class TrayManager:
    def __init__(self, app_controller):
        self.app_controller = app_controller  # <-- correction B
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self._load_icon())
        self.tray.setToolTip("Call Note Recorder")

        menu = QMenu()
        self.show_action = QAction("Show / Hide", menu)
        self.devices_action = QAction("Audio devices…", menu)
        self.quit_action = QAction("Quit", menu)
        self.show_action.triggered.connect(app_controller.toggle_visibility)
        self.devices_action.triggered.connect(app_controller.open_device_settings)
        self.quit_action.triggered.connect(app_controller.quit_app)
        menu.addAction(self.show_action)
        menu.addAction(self.devices_action)
        menu.addSeparator()
        menu.addAction(self.quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        self.tray.show()

    @staticmethod
    def _load_icon() -> QIcon:
        if os.path.exists(TRAY_ICON):
            return QIcon(TRAY_ICON)
        # Fallback: a simple solid dot so the app still has a tray presence.
        pix = QPixmap(32, 32)
        pix.fill(QColor(28, 28, 30))
        return QIcon(pix)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.app_controller.toggle_visibility()
