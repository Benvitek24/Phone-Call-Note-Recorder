"""All QSS stylesheets and shared style constants in one place (spec rule)."""

# ---- Status colors (spec) -------------------------------------------------
STATUS_COLORS = {
    "loading":      "#888888",
    "ready":        "#888888",
    "recording":    "#FF3B30",
    "transcribing": "#FF9F0A",
    "summarizing":  "#30D158",
    "done":         "#888888",
    "error":        "#FF3B30",
}

SPEAKER_YOU_COLOR      = "#AADDFF"
SPEAKER_CUSTOMER_COLOR = "#FFDDAA"

# ---- Widget backgrounds ---------------------------------------------------
ICON_BG   = "rgba(28, 28, 30, 0.88)"
PANEL_BG  = "rgba(20, 20, 22, 0.90)"
TOPBAR_BG = "rgba(15, 15, 17, 0.95)"

# ---- Stylesheets ----------------------------------------------------------
ICON_WIDGET_QSS = """
#iconRoot {
    background-color: rgba(28, 28, 30, 0.88);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 18px;
}
#recordButton {
    border-radius: 18px;
}
#timerLabel {
    color: #AAAAAA;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 10px;
}
"""

PANEL_QSS = """
#panelRoot {
    background-color: rgba(20, 20, 22, 0.90);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 12px;
}
#topBar {
    background-color: rgba(15, 15, 17, 0.95);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
#timerLabel {
    color: #CCCCCC;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
    min-width: 44px;
}
#statusLabel { font-size: 13px; }

#warningBanner {
    background-color: rgba(255, 159, 10, 0.15);
    border: 1px solid rgba(255, 159, 10, 0.30);
    color: #FF9F0A;
    font-size: 12px;
    padding: 4px 10px;
}
#updateBanner {
    background-color: rgba(48, 209, 88, 0.15);
    border: 1px solid rgba(48, 209, 88, 0.30);
    color: #30D158;
    font-size: 12px;
    padding: 4px 10px;
}

QPushButton#columnHeader {
    background-color: rgba(35, 35, 38, 0.6);
    color: #CCCCCC;
    font-size: 12px;
    font-weight: 500;
    border: none;
    text-align: center;
}
QPushButton#columnHeader:hover { background-color: rgba(45, 45, 48, 0.7); }

#actionBar { background-color: rgba(15, 15, 17, 0.6); }

QTextEdit, QLabel#contentLabel {
    background: transparent;
    color: #F0F0F0;
    font-size: 13px;
    border: none;
}
QTextEdit { padding: 12px; }

/* My Notes: look obviously like a clickable text box (review #3) */
QTextEdit#notesEditor {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 6px;
}
QTextEdit#notesEditor:focus {
    border: 1px solid rgba(48, 209, 88, 0.60);
}

/* CRM copy header field (review #5) */
#headerRow { background-color: rgba(15, 15, 17, 0.6); }
#headerLabel { color: #999999; font-size: 12px; }
QLineEdit#headerEdit {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    color: #F0F0F0;
    font-size: 12px;
    padding: 3px 8px;
}
QLineEdit#headerEdit:focus { border: 1px solid rgba(255, 255, 255, 0.30); }

QScrollBar:vertical {
    background: transparent; width: 8px; margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.18); border-radius: 4px; min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QPushButton {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 6px;
    color: #DDDDDD;
    font-size: 12px;
    padding: 4px 10px;
}
QPushButton:hover  { background-color: rgba(255, 255, 255, 0.14); }
QPushButton:pressed { background-color: rgba(255, 255, 255, 0.20); }
QPushButton:disabled { color: #666666; }

QPushButton#deleteButton {
    background-color: rgba(255, 59, 48, 0.15);
    border: 1px solid rgba(255, 59, 48, 0.30);
    color: #FF3B30;
}
QPushButton#deleteButton:hover { background-color: rgba(255, 59, 48, 0.25); }

QPushButton#closeButton:hover { background-color: rgba(255, 59, 48, 0.20); }
"""
