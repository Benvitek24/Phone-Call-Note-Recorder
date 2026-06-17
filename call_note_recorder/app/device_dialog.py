"""Audio device picker.

Lets the rep choose their microphone and the call-audio (output) source, so the
app isn't at the mercy of whatever Windows set as default. Choices are stored by
device NAME (stable across re-plugs) in config.json.
"""

from PyQt6.QtWidgets import (
    QDialog, QComboBox, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
)

from core.audio_recorder import list_input_devices, list_output_devices

_DIALOG_QSS = """
QDialog { background-color: #1c1c1e; }
QLabel { color: #DDDDDD; font-size: 13px; }
QComboBox {
    background: rgba(255,255,255,0.08); color: #F0F0F0;
    border: 1px solid rgba(255,255,255,0.15); border-radius: 6px;
    padding: 5px 8px; font-size: 13px; min-width: 360px;
}
QComboBox QAbstractItemView {
    background: #2a2a2e; color: #F0F0F0; selection-background-color: #3a6ea5;
}
QPushButton {
    background: rgba(255,255,255,0.10); color: #DDDDDD;
    border: 1px solid rgba(255,255,255,0.15); border-radius: 6px;
    padding: 6px 16px; font-size: 13px;
}
QPushButton:hover { background: rgba(255,255,255,0.16); }
QPushButton#saveBtn { background: rgba(48,209,88,0.22); border-color: rgba(48,209,88,0.5); color: #30D158; }
"""


def _select_by_data(combo: QComboBox, value):
    for i in range(combo.count()):
        if combo.itemData(i) == value:
            combo.setCurrentIndex(i)
            return
    combo.setCurrentIndex(0)  # fall back to "Automatic"


def choose_devices(parent, current_mic, current_output):
    """Show the picker modally. Returns (mic_name, output_name) on Save (either
    may be None = automatic), or None if cancelled."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("Audio devices")
    dlg.setStyleSheet(_DIALOG_QSS)
    dlg.setModal(True)

    v = QVBoxLayout(dlg)
    v.setContentsMargins(18, 18, 18, 18)
    v.setSpacing(8)

    v.addWidget(QLabel("Your microphone (your voice):"))
    mic_combo = QComboBox()
    mic_combo.addItem("Automatic (Windows default)", None)
    for d in list_input_devices():
        mic_combo.addItem(d['name'], d['name'])
    v.addWidget(mic_combo)

    v.addSpacing(6)
    v.addWidget(QLabel("Call audio — the customer (what you hear):"))
    out_combo = QComboBox()
    out_combo.addItem("Automatic (Windows default)", None)
    for d in list_output_devices():
        label = d['name'] if d['has_loopback'] else f"{d['name']}  (no loopback available)"
        out_combo.addItem(label, d['name'])
    v.addWidget(out_combo)

    hint = QLabel("Tip: pick the headset/speakers you actually use for calls. "
                  "Changes apply on your next recording.")
    hint.setStyleSheet("color: #888888; font-size: 11px;")
    hint.setWordWrap(True)
    v.addWidget(hint)

    _select_by_data(mic_combo, current_mic)
    _select_by_data(out_combo, current_output)

    v.addSpacing(8)
    h = QHBoxLayout()
    h.addStretch(1)
    cancel = QPushButton("Cancel")
    save = QPushButton("Save")
    save.setObjectName("saveBtn")
    cancel.clicked.connect(dlg.reject)
    save.clicked.connect(dlg.accept)
    h.addWidget(cancel)
    h.addWidget(save)
    v.addLayout(h)

    if dlg.exec() == QDialog.DialogCode.Accepted:
        return mic_combo.currentData(), out_combo.currentData()
    return None
