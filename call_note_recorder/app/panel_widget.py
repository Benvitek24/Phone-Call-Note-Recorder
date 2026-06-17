"""Expanded 3-column panel: Transcript | Summary | My Notes.

Frameless, translucent, always-on-top, Acrylic blur. Implements drag-to-move
(top bar) and edge resize.

Correction folded in (review item A): the spec defined mouseMoveEvent TWICE
(once for drag, once for resize-cursor), so drag silently broke. Here move +
resize + hover-cursor all live in ONE mouseMoveEvent / mousePressEvent /
mouseReleaseEvent set.
"""

import html

from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QTextEdit, QHBoxLayout, QVBoxLayout,
    QApplication, QSizePolicy,
)

from app.styles import (
    PANEL_QSS, STATUS_COLORS, SPEAKER_YOU_COLOR, SPEAKER_CUSTOMER_COLOR,
)
from app.win32_effects import apply_acrylic

TOPBAR_HEIGHT = 44
RESIZE_MARGIN = 8
MIN_W, MIN_H = 600, 350
COLLAPSED_W = 32
_MAXSIZE = 16777215  # Qt's QWIDGETSIZE_MAX


class _Column(QWidget):
    """One panel column: header (collapse toggle) + content + action bar."""

    def __init__(self, title: str, editable: bool, placeholder: str = ""):
        super().__init__()
        self.title = title
        self.collapsed = False

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self.header = QPushButton(f"{title} ▾")
        self.header.setObjectName("columnHeader")
        self.header.setFixedHeight(36)

        self.content = QTextEdit()
        self.content.setReadOnly(not editable)
        if placeholder:
            self.content.setPlaceholderText(placeholder)
        self.content.setSizePolicy(QSizePolicy.Policy.Expanding,
                                   QSizePolicy.Policy.Expanding)

        self.action_bar = QWidget()
        self.action_bar.setObjectName("actionBar")
        self.action_bar.setFixedHeight(36)
        self.action_layout = QHBoxLayout(self.action_bar)
        self.action_layout.setContentsMargins(8, 4, 8, 4)
        self.action_layout.setSpacing(6)

        v.addWidget(self.header)
        v.addWidget(self.content, 1)
        v.addWidget(self.action_bar)

    def set_collapsed(self, collapsed: bool):
        self.collapsed = collapsed
        if collapsed:
            self.header.setText(self.title[0])
            self.content.hide()
            self.action_bar.hide()
            self.setFixedWidth(COLLAPSED_W)
        else:
            self.header.setText(f"{self.title} ▾")
            self.content.show()
            self.action_bar.show()
            self.setMinimumWidth(0)
            self.setMaximumWidth(_MAXSIZE)


class PanelWidget(QWidget):
    # Top bar
    record_clicked   = pyqtSignal()   # main_window decides record vs stop by state
    delete_clicked   = pyqtSignal()
    minimize_clicked = pyqtSignal()
    close_clicked    = pyqtSignal()
    # Column actions
    copy_transcript  = pyqtSignal()
    copy_summary     = pyqtSignal()
    copy_notes       = pyqtSignal()
    save_clicked     = pyqtSignal()
    retry_clicked    = pyqtSignal()
    # Banners
    download_update_clicked = pyqtSignal()
    # CRM copy header (review #5)
    header_changed = pyqtSignal(str)
    # Geometry persistence
    geometry_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("panelRoot")
        self.setStyleSheet(PANEL_QSS)
        self.setMinimumSize(MIN_W, MIN_H)
        self.setMouseTracking(True)

        # interaction state
        self._mode = None            # 'move' | 'resize' | None
        self._drag_offset = QPoint()
        self._resize_edges = ()
        self._press_global = QPoint()
        self._start_geom = QRect()

        self._build_ui()
        self._apply_max_width()

    # ----------------------------------------------------------------- build
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        # Banners (hidden by default)
        self.warning_banner = QLabel(
            "Customer audio not detected — recording your mic only."
        )
        self.warning_banner.setObjectName("warningBanner")
        self.warning_banner.hide()
        root.addWidget(self.warning_banner)

        self.update_banner = QPushButton("")
        self.update_banner.setObjectName("updateBanner")
        self.update_banner.clicked.connect(self.download_update_clicked.emit)
        self.update_banner.hide()
        root.addWidget(self.update_banner)

        # CRM copy header (review #5): editable, prepended when copying the
        # Summary or My Notes. Persisted to config between sessions.
        header_row = QWidget()
        header_row.setObjectName("headerRow")
        hr = QHBoxLayout(header_row)
        hr.setContentsMargins(12, 4, 12, 4)
        hr.setSpacing(8)
        hr_label = QLabel("Copy header:")
        hr_label.setObjectName("headerLabel")
        from PyQt6.QtWidgets import QLineEdit
        self.header_edit = QLineEdit()
        self.header_edit.setObjectName("headerEdit")
        self.header_edit.setPlaceholderText("(no header)")
        self.header_edit.editingFinished.connect(
            lambda: self.header_changed.emit(self.header_edit.text()))
        hr.addWidget(hr_label)
        hr.addWidget(self.header_edit, 1)
        root.addWidget(header_row)

        # Columns
        self.columns_host = QWidget()
        self.col_layout = QHBoxLayout(self.columns_host)
        self.col_layout.setContentsMargins(0, 0, 0, 0)
        self.col_layout.setSpacing(1)

        # Transcript + Summary are editable too (review #2) — you can fix a
        # mis-hearing or tweak the note before copying.
        self.col_transcript = _Column("Transcript", editable=True)
        self.col_summary    = _Column("Summary", editable=True)
        self.col_notes      = _Column("My Notes", editable=True,
                                      placeholder="Click here and type your own note...")
        self.col_notes.content.setObjectName("notesEditor")  # styled to look clickable (#3)
        self._columns = [self.col_transcript, self.col_summary, self.col_notes]
        # Reset the Save button's confirmed state once the note is edited (#4).
        self.col_notes.content.textChanged.connect(self._reset_save_button)

        # Action-bar buttons
        self.btn_copy_transcript = self._mk_button("Copy", self.copy_transcript.emit)
        self.col_transcript.action_layout.addStretch(1)
        self.col_transcript.action_layout.addWidget(self.btn_copy_transcript)

        self.btn_retry = self._mk_button("Retry", self.retry_clicked.emit)
        self.btn_retry.setObjectName("retryButton")
        self.btn_retry.hide()
        self.btn_copy_summary = self._mk_button("Copy", self.copy_summary.emit)
        self.col_summary.action_layout.addWidget(self.btn_retry)
        self.col_summary.action_layout.addStretch(1)
        self.col_summary.action_layout.addWidget(self.btn_copy_summary)

        self.btn_save = self._mk_button("Save", self.save_clicked.emit)
        self.btn_copy_notes = self._mk_button("Copy", self.copy_notes.emit)
        self.col_notes.action_layout.addWidget(self.btn_save)
        self.col_notes.action_layout.addStretch(1)
        self.col_notes.action_layout.addWidget(self.btn_copy_notes)

        for c in self._columns:
            c.header.clicked.connect(lambda _=False, col=c: self._toggle_column(col))
            self.col_layout.addWidget(c, 1)

        root.addWidget(self.columns_host, 1)

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topBar")
        bar.setFixedHeight(TOPBAR_HEIGHT)
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(8)

        self.record_btn = QPushButton("●")
        self.record_btn.setFixedSize(28, 28)
        self.record_btn.setStyleSheet("border-radius: 14px;")
        self.record_btn.clicked.connect(self.record_clicked.emit)

        self.timer_label = QLabel("00:00")
        self.timer_label.setObjectName("timerLabel")

        self.status_label = QLabel("Loading...")
        self.status_label.setObjectName("statusLabel")
        self.set_status("Loading...", "loading")

        self.btn_delete = self._mk_button("Delete", self.delete_clicked.emit)
        self.btn_delete.setObjectName("deleteButton")
        self.btn_delete.hide()

        self.btn_min = self._mk_button("—", self.minimize_clicked.emit)
        self.btn_min.setFixedWidth(28)
        self.btn_close = self._mk_button("✕", self.close_clicked.emit)
        self.btn_close.setObjectName("closeButton")
        self.btn_close.setFixedWidth(28)

        h.addWidget(self.record_btn)
        h.addWidget(self.timer_label)
        h.addWidget(self.status_label)
        h.addStretch(1)
        h.addWidget(self.btn_delete)
        h.addWidget(self.btn_min)
        h.addWidget(self.btn_close)
        return bar

    @staticmethod
    def _mk_button(text, slot) -> QPushButton:
        b = QPushButton(text)
        b.clicked.connect(slot)
        return b

    # --------------------------------------------------------------- columns
    def _toggle_column(self, col: _Column):
        open_cols = [c for c in self._columns if not c.collapsed]
        # Don't allow collapsing the last open column.
        if not col.collapsed and len(open_cols) == 1:
            return
        col.set_collapsed(not col.collapsed)
        # Re-stretch: expanded columns share space, collapsed are fixed width.
        for c in self._columns:
            self.col_layout.setStretchFactor(c, 0 if c.collapsed else 1)

    # ------------------------------------------------------- public UI API
    def set_status(self, text: str, color_key: str):
        color = STATUS_COLORS.get(color_key, "#888888")
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"font-size: 13px; color: {color};")

    def set_timer(self, text: str):
        self.timer_label.setText(text)

    def set_record_button_recording(self, recording: bool):
        if recording:
            self.record_btn.setText("■")
            self.record_btn.setStyleSheet(
                "border-radius: 14px; background-color: #FF3B30; color: white;"
            )
        else:
            self.record_btn.setText("●")
            self.record_btn.setStyleSheet("border-radius: 14px;")

    def set_delete_visible(self, visible: bool):
        self.btn_delete.setVisible(visible)

    # transcript
    def append_transcript_segment(self, speaker: str, text: str):
        color = SPEAKER_YOU_COLOR if speaker == "You" else SPEAKER_CUSTOMER_COLOR
        safe = html.escape(text)
        self.col_transcript.content.append(
            f'<span style="color:{color};font-weight:bold">{html.escape(speaker)}:</span> '
            f'{safe}<br>'
        )

    def set_transcript(self, text: str):
        """Replace live stream with the final, time-ordered transcript."""
        self.col_transcript.content.clear()
        for block in text.split("\n\n"):
            if not block.strip():
                continue
            if ":" in block:
                speaker, rest = block.split(":", 1)
                speaker = speaker.strip()
                color = (SPEAKER_YOU_COLOR if speaker == "You"
                         else SPEAKER_CUSTOMER_COLOR)
                self.col_transcript.content.append(
                    f'<span style="color:{color};font-weight:bold">'
                    f'{html.escape(speaker)}:</span>{html.escape(rest)}<br>'
                )
            else:
                self.col_transcript.content.append(html.escape(block))

    def append_transcript_note(self, message: str):
        self.col_transcript.content.append(
            f'<br><span style="color:#FF9F0A;font-size:12px">{html.escape(message)}</span>'
        )

    def get_transcript_text(self) -> str:
        return self.col_transcript.content.toPlainText()

    # summary
    def clear_summary(self):
        self.col_summary.content.clear()
        self.btn_retry.hide()

    def append_summary_chunk(self, chunk: str):
        c = self.col_summary.content.textCursor()
        c.movePosition(c.MoveOperation.End)
        c.insertText(chunk)
        self.col_summary.content.setTextCursor(c)
        self.col_summary.content.ensureCursorVisible()

    def append_summary_text(self, text: str):
        self.col_summary.content.append(text)

    def get_summary_text(self) -> str:
        return self.col_summary.content.toPlainText()

    def show_summary_retry(self):
        self.btn_retry.show()

    # notes
    def get_notes_text(self) -> str:
        return self.col_notes.content.toPlainText()

    def clear_all_content(self):
        self.col_transcript.content.clear()
        self.col_summary.content.clear()
        self.col_notes.content.clear()
        self.btn_retry.hide()

    def show_saved_confirmation(self, count: int):
        # Stronger, persistent confirmation (review #4): green button with the
        # running example count, stays until the note is edited again.
        self.btn_save.setText(f"Saved ✓  ({count} saved)")
        self.btn_save.setStyleSheet(
            "background-color: rgba(48, 209, 88, 0.25);"
            " border: 1px solid rgba(48, 209, 88, 0.55); color: #30D158;"
        )

    def _reset_save_button(self):
        if self.btn_save.text() != "Save":
            self.btn_save.setText("Save")
            self.btn_save.setStyleSheet("")  # back to default QSS

    def focus_notes(self):
        self.col_notes.content.setFocus()

    # CRM copy header (review #5)
    def set_crm_header(self, text: str):
        self.header_edit.setText(text or "")

    def get_crm_header(self) -> str:
        return self.header_edit.text().strip()

    # banners
    def show_loopback_warning(self):
        self.warning_banner.show()

    def hide_loopback_warning(self):
        self.warning_banner.hide()

    def show_update_banner(self, version: str):
        self.update_banner.setText(f"Version {version} available   [Download Update]")
        self.update_banner.show()

    # ------------------------------------------------------------- geometry
    def _apply_max_width(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.setMaximumWidth(int(screen.width() * 0.5))

    def place_default_bottom_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        w = int(screen.width() * 0.40)
        h = int(screen.height() * 0.35)
        w = max(MIN_W, min(w, int(screen.width() * 0.5)))
        h = max(MIN_H, h)
        x = screen.right() - w - 20
        y = screen.bottom() - h - 20
        self.setGeometry(x, y, w, h)

    def apply_saved_geometry(self, geom: dict):
        screen = QApplication.primaryScreen().availableGeometry()
        x, y = geom.get('x'), geom.get('y')
        w = geom.get('width') or int(screen.width() * 0.40)
        h = geom.get('height') or int(screen.height() * 0.35)
        w = max(MIN_W, min(w, int(screen.width() * 0.5)))
        h = max(MIN_H, h)
        # Off-screen / unset -> default bottom-right.
        on_screen = (
            x is not None and y is not None and
            x >= screen.left() - 50 and y >= screen.top() - 50 and
            x < screen.right() - 50 and y < screen.bottom() - 50
        )
        if not on_screen:
            x = screen.right() - w - 20
            y = screen.bottom() - h - 20
        self.setGeometry(int(x), int(y), w, h)

    # ----------------------------------------------------- mouse (move+resize)
    def _edges_at(self, pos: QPoint):
        on_left   = pos.x() < RESIZE_MARGIN
        on_right  = pos.x() > self.width() - RESIZE_MARGIN
        on_top    = pos.y() < RESIZE_MARGIN
        on_bottom = pos.y() > self.height() - RESIZE_MARGIN
        edges = []
        if on_left:   edges.append('left')
        if on_right:  edges.append('right')
        if on_top:    edges.append('top')
        if on_bottom: edges.append('bottom')
        return tuple(edges)

    def _cursor_for_edges(self, edges):
        s = set(edges)
        if ('left' in s and 'top' in s) or ('right' in s and 'bottom' in s):
            return Qt.CursorShape.SizeFDiagCursor
        if ('right' in s and 'top' in s) or ('left' in s and 'bottom' in s):
            return Qt.CursorShape.SizeBDiagCursor
        if 'left' in s or 'right' in s:
            return Qt.CursorShape.SizeHorCursor
        if 'top' in s or 'bottom' in s:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        edges = self._edges_at(pos)
        if edges:
            self._mode = 'resize'
            self._resize_edges = edges
            self._press_global = event.globalPosition().toPoint()
            self._start_geom = self.geometry()
        elif pos.y() < TOPBAR_HEIGHT:
            self._mode = 'move'
            self._drag_offset = (event.globalPosition().toPoint()
                                 - self.frameGeometry().topLeft())
        else:
            self._mode = None

    def mouseMoveEvent(self, event):
        # Hover (no button) -> update the resize cursor.
        if event.buttons() == Qt.MouseButton.NoButton:
            self.setCursor(self._cursor_for_edges(self._edges_at(
                event.position().toPoint())))
            return

        if self._mode == 'move':
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        elif self._mode == 'resize':
            self._do_resize(event.globalPosition().toPoint())

    def mouseReleaseEvent(self, event):
        if self._mode in ('move', 'resize'):
            self.geometry_changed.emit()
        self._mode = None
        self._resize_edges = ()

    def _do_resize(self, global_pos: QPoint):
        delta = global_pos - self._press_global
        g = QRect(self._start_geom)
        min_w = self.minimumWidth()
        min_h = self.minimumHeight()
        max_w = self.maximumWidth()

        if 'left' in self._resize_edges:
            new_left = g.left() + delta.x()
            new_left = min(new_left, g.right() - min_w)
            new_left = max(new_left, g.right() - max_w)
            g.setLeft(new_left)
        if 'right' in self._resize_edges:
            new_right = g.right() + delta.x()
            new_right = max(new_right, g.left() + min_w)
            new_right = min(new_right, g.left() + max_w)
            g.setRight(new_right)
        if 'top' in self._resize_edges:
            g.setTop(min(g.top() + delta.y(), g.bottom() - min_h))
        if 'bottom' in self._resize_edges:
            g.setBottom(max(g.bottom() + delta.y(), g.top() + min_h))

        self.setGeometry(g)

    # ----------------------------------------------------------------- show
    def showEvent(self, event):
        super().showEvent(event)
        apply_acrylic(int(self.winId()))
