"""Small floating glassmorphic record button (always present while running)."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout

from app.styles import ICON_WIDGET_QSS
from app.win32_effects import apply_acrylic

ICON_SIZE = 68
EDGE_MARGIN = 20


class IconWidget(QWidget):
    clicked = pyqtSignal()  # record button pressed

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(ICON_SIZE, ICON_SIZE)
        self.setObjectName("iconRoot")
        self.setStyleSheet(ICON_WIDGET_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 6)
        layout.setSpacing(2)

        self.record_btn = QPushButton("●")
        self.record_btn.setObjectName("recordButton")
        self.record_btn.setFixedSize(36, 36)
        self.record_btn.setEnabled(False)  # disabled until models load
        self.record_btn.setToolTip("Loading...")
        self.record_btn.clicked.connect(self.clicked.emit)
        self._set_idle_style()

        self.timer_label = QLabel("")
        self.timer_label.setObjectName("timerLabel")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(self.record_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.timer_label)

        # Pulse animation state
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_step)
        self._pulse_value = 255
        self._pulse_direction = -1

        self._position_bottom_right()

    # ---- positioning ------------------------------------------------------
    def _position_bottom_right(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - EDGE_MARGIN
        y = screen.bottom() - self.height() - EDGE_MARGIN
        self.move(x, y)

    # ---- enable / state ---------------------------------------------------
    def set_ready(self):
        self.record_btn.setEnabled(True)
        self.record_btn.setToolTip("Ready")

    def set_loading_tooltip(self, text: str):
        self.record_btn.setToolTip(text)

    def show_idle(self):
        self.stop_pulse()
        self.timer_label.setText("")
        self._set_idle_style()

    def show_recording(self):
        self.start_pulse()

    def set_timer_text(self, text: str):
        self.timer_label.setText(text)

    # ---- styles -----------------------------------------------------------
    def _set_idle_style(self):
        self.record_btn.setText("●")
        self.record_btn.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.15); border-radius: 18px;"
            " color: #FFFFFF; font-size: 16px;"
        )

    # ---- pulse ------------------------------------------------------------
    def start_pulse(self):
        self.record_btn.setText("●")
        self._pulse_value = 255
        self._pulse_direction = -1
        self._pulse_timer.start(30)

    def stop_pulse(self):
        self._pulse_timer.stop()

    def _pulse_step(self):
        self._pulse_value += self._pulse_direction * 8
        if self._pulse_value <= 140:
            self._pulse_value = 140
            self._pulse_direction = 1
        elif self._pulse_value >= 255:
            self._pulse_value = 255
            self._pulse_direction = -1
        alpha = self._pulse_value / 255.0
        self.record_btn.setStyleSheet(
            f"background-color: rgba(255, 59, 48, {alpha:.2f}); border-radius: 18px;"
            f" color: #FFFFFF; font-size: 16px;"
        )

    # ---- acrylic ----------------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        apply_acrylic(int(self.winId()))
