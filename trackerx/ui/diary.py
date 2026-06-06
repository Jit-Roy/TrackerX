from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QPixmap, QIcon, QTextCharFormat,
    QTextBlockFormat, QTextCursor,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.models import DiaryEntry
from ..core.services import ProductivityService


# ── Palette — mirrors app-wide strict B&W/grey scheme ─────────────────────────
_BG           = "#111111"
_SIDEBAR_BG   = _BG
_CARD_HOV     = "rgba(255,255,255,0.025)"
_CARD_SEL     = "rgba(255,255,255,0.05)"
_BORDER       = "rgba(255,255,255,0.06)"
_BORDER_MID   = "rgba(255,255,255,0.10)"
_BORDER_SEL   = "rgba(255,255,255,0.22)"
_DIVIDER      = "rgba(255,255,255,0.05)"
_T_PRI        = "#e8e8ed"
_T_SEC        = "#8e8e93"
_T_TER        = "#48484a"
_T_DIM        = "#2a2a2c"
_SURFACE_IN   = "#1c1c1c"
_MONO         = "Courier New"

_SIDEBAR_W    = 236
_AUTOSAVE_MS  = 850      # debounce window before writing to service


# ── Thin rules ─────────────────────────────────────────────────────────────────

def _hdiv(color: str = _DIVIDER) -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background: {color}; border: none;")
    return f


def _vdiv(color: str = _DIVIDER) -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setFixedWidth(1)
    f.setStyleSheet(f"background: {color}; border: none;")
    return f


# ── Delete icon ────────────────────────────────────────────────────────────────

def _trash_icon(color: str = _T_TER) -> QIcon:
    pix = QPixmap(16, 16)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.3)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    # lid
    p.drawLine(4, 5, 12, 5)
    p.drawLine(6, 5, 6, 3)
    p.drawLine(10, 5, 10, 3)
    p.drawLine(6, 3, 10, 3)
    # body
    p.drawLine(5, 6, 5, 13)
    p.drawLine(11, 6, 11, 13)
    p.drawLine(5, 13, 11, 13)
    # inner lines
    p.drawLine(8, 7, 8, 12)
    p.end()
    return QIcon(pix)


# ── Sidebar entry item ─────────────────────────────────────────────────────────

class _EntryItem(QWidget):
    """
    One diary date row in the sidebar.

    ┌──────────────────────────────────────────┐
    │  07   │  Monday (or TODAY)               │
    │  JUN  │  First line of entry or  —       │
    └──────────────────────────────────────────┘
    """

    date_clicked = Signal(date)

    _IDLE = "QWidget#EI { background: transparent; }"
    _HOV  = "QWidget#EI { background: " + _CARD_HOV + "; }"
    _SEL  = (
        "QWidget#EI {"
        f"  background: {_CARD_SEL};"
        f"  border-left: 2px solid {_BORDER_SEL};"
        "}"
    )

    def __init__(
        self,
        entry_date: date,
        snippet: str = "",
        selected: bool = False,
        is_today: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("EI")
        self.entry_date = entry_date
        self.selected   = selected
        self.is_today   = is_today
        self._hov       = False

        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(56)
        self._build(snippet)
        self._restyle()

    def _build(self, snippet: str) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(10)

        # ── Date column ────────────────────────────────────────────────────
        date_box = QWidget()
        date_box.setFixedWidth(34)
        date_box.setStyleSheet("background: transparent;")
        db = QVBoxLayout(date_box)
        db.setContentsMargins(0, 0, 0, 0)
        db.setSpacing(1)

        pri_color = _T_PRI if self.is_today else _T_SEC
        day_num = QLabel(f"{self.entry_date.day:02d}")
        day_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        day_num.setStyleSheet(
            f"color: {pri_color};"
            f"font-size: 11pt; font-weight: {'700' if self.is_today else '500'};"
            f"font-family: '{_MONO}'; background: transparent; letter-spacing: -0.5px;"
        )
        db.addWidget(day_num)

        mon = QLabel(self.entry_date.strftime("%b").upper())
        mon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mon.setStyleSheet(
            f"color: {_T_DIM}; font-size: 5.8pt; letter-spacing: 0.7px;"
            "background: transparent;"
        )
        db.addWidget(mon)
        lay.addWidget(date_box)

        # Thin vertical hairline
        vsep = QWidget()
        vsep.setFixedSize(1, 22)
        vsep.setStyleSheet(f"background: {_DIVIDER};")
        lay.addWidget(vsep, alignment=Qt.AlignmentFlag.AlignVCenter)

        # ── Info column ────────────────────────────────────────────────────
        info = QWidget()
        info.setStyleSheet("background: transparent;")
        il = QVBoxLayout(info)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(3)

        weekday_text = "TODAY" if self.is_today else self.entry_date.strftime("%A")
        wday = QLabel(weekday_text)
        wday.setStyleSheet(
            f"color: {pri_color};"
            f"font-size: {'7.5' if self.is_today else '8'}pt;"
            f"font-weight: {'700' if self.is_today else '400'};"
            f"letter-spacing: {'1.0' if self.is_today else '0'}px;"
            "background: transparent;"
        )
        il.addWidget(wday)

        snip_raw = (snippet or "").strip().split("\n")[0]
        snip_text = (snip_raw[:42] + "…") if len(snip_raw) > 42 else (snip_raw or "—")
        snip = QLabel(snip_text)
        snip.setStyleSheet(
            f"color: {_T_TER}; font-size: 7.5pt; background: transparent;"
        )
        il.addWidget(snip)
        lay.addWidget(info, 1)

    def _restyle(self) -> None:
        if self.selected:
            self.setStyleSheet(self._SEL)
        elif self._hov:
            self.setStyleSheet(self._HOV)
        else:
            self.setStyleSheet(self._IDLE)

    def set_selected(self, val: bool) -> None:
        self.selected = val
        self._restyle()

    def enterEvent(self, _) -> None:
        self._hov = True
        self._restyle()

    def leaveEvent(self, _) -> None:
        self._hov = False
        self._restyle()

    def mousePressEvent(self, _) -> None:
        self.date_clicked.emit(self.entry_date)


# ── Sidebar ────────────────────────────────────────────────────────────────────

class _Sidebar(QWidget):
    """
    Left panel: all diary entries, newest-first, grouped by calendar month.
    Always shows today at the top even when no entry exists yet.
    """

    date_selected = Signal(date)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(_SIDEBAR_W)
        self.setStyleSheet(f"background: {_SIDEBAR_BG};")
        self._items: list[_EntryItem] = []
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setFixedHeight(50)
        hdr.setStyleSheet(f"background: {_SIDEBAR_BG};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(14, 0, 14, 0)
        title = QLabel("JOURNAL")
        title.setStyleSheet(
            f"color: {_T_DIM}; font-size: 6.8pt; font-weight: 700;"
            f"letter-spacing: 1.8px; background: transparent;"
        )
        hl.addWidget(title)
        hl.addStretch()
        lay.addWidget(hdr)
        lay.addWidget(_hdiv())

        # Scrollable list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {_SIDEBAR_BG}; border: none; }}"
            "QScrollBar:vertical { width: 3px; background: transparent; margin: 0; }"
            "QScrollBar::handle:vertical {"
            "  background: rgba(255,255,255,0.07); border-radius: 1px; min-height: 20px;"
            "}"
            "QScrollBar::add-line, QScrollBar::sub-line { height: 0; }"
            "QScrollBar::add-page, QScrollBar::sub-page { height: 0; }"
        )

        self._body = QWidget()
        self._body.setStyleSheet(f"background: {_SIDEBAR_BG};")
        self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(0, 6, 0, 14)
        self._body_lay.setSpacing(0)
        self._body_lay.addStretch(1)

        scroll.setWidget(self._body)
        lay.addWidget(scroll, 1)

    # ── Month separator label ──────────────────────────────────────────────

    @staticmethod
    def _month_label(d: date) -> QLabel:
        lbl = QLabel(d.strftime("%B %Y").upper())
        lbl.setStyleSheet(
            f"color: {_T_DIM}; font-size: 6.5pt; font-weight: 700;"
            f"letter-spacing: 1.3px; background: transparent;"
            f"padding: 14px 14px 4px 14px;"
        )
        return lbl

    # ── Populate ───────────────────────────────────────────────────────────

    def populate(self, entries: list[DiaryEntry], selected_date: date | None = None) -> None:
        # Wipe existing widgets
        while self._body_lay.count():
            item = self._body_lay.takeAt(0)
            if w := item.widget():
                w.deleteLater()
        self._items = []

        today = date.today()

        # Build a date → entry mapping; always include today
        date_map: dict[date, DiaryEntry | None] = {e.entry_date: e for e in entries}
        if today not in date_map:
            date_map[today] = None   # synthetic placeholder — no content yet

        sorted_dates = sorted(date_map.keys(), reverse=True)

        current_month: tuple[int, int] | None = None
        for d in sorted_dates:
            month_key = (d.year, d.month)
            if month_key != current_month:
                current_month = month_key
                self._body_lay.addWidget(self._month_label(d))

            entry   = date_map[d]
            snippet = entry.content if entry else ""
            is_sel  = (d == selected_date)
            is_today= (d == today)

            item_w = _EntryItem(d, snippet=snippet, selected=is_sel, is_today=is_today)
            item_w.date_clicked.connect(self.date_selected.emit)
            self._body_lay.addWidget(item_w)
            self._items.append(item_w)

        self._body_lay.addStretch(1)

    def set_selection(self, d: date) -> None:
        for item in self._items:
            item.set_selected(item.entry_date == d)


# ── Writing pane ───────────────────────────────────────────────────────────────

class _WritingPane(QWidget):
    """
    Right panel: date nav bar → editor → footer.

    Emits content_changed on every keystroke so the parent can debounce saves.
    """

    content_changed = Signal(str)
    delete_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Navigation bar ─────────────────────────────────────────────────
        nav = QWidget()
        nav.setFixedHeight(56)
        nav.setStyleSheet(f"background: {_BG};")
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(56, 0, 56, 0)
        nl.setSpacing(0)

        self.prev_btn = self._arrow("‹")
        nl.addWidget(self.prev_btn)
        nl.addSpacing(16)

        self.date_lbl = QLabel()
        self.date_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_lbl.setStyleSheet(
            f"color: {_T_PRI}; font-size: 11pt; font-weight: 600;"
            f"letter-spacing: -0.2px; background: transparent;"
        )
        nl.addWidget(self.date_lbl, 1)

        self.today_btn = QPushButton("Today")
        self.today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.today_btn.setStyleSheet(
            f"QPushButton {{ color: {_T_TER}; background: transparent; border: none;"
            f"font-size: 8pt; letter-spacing: 0.2px; }}"
            f"QPushButton:hover {{ color: {_T_SEC}; }}"
        )
        nl.addWidget(self.today_btn)
        nl.addSpacing(16)

        self.next_btn = self._arrow("›")
        nl.addWidget(self.next_btn)

        lay.addWidget(nav)
        lay.addWidget(_hdiv())

        # ── Editor area ────────────────────────────────────────────────────
        editor_wrap = QWidget()
        editor_wrap.setStyleSheet(f"background: {_BG};")
        ew = QVBoxLayout(editor_wrap)
        ew.setContentsMargins(56, 28, 56, 16)
        ew.setSpacing(0)

        # Relative date label (TODAY / YESTERDAY / N DAYS AGO)
        self.sub_lbl = QLabel()
        self.sub_lbl.setStyleSheet(
            f"color: {_T_TER}; font-size: 7pt; font-weight: 700;"
            f"letter-spacing: 1.6px; background: transparent;"
        )
        ew.addWidget(self.sub_lbl)
        ew.addSpacing(22)

        # Main editor
        self.editor = QTextEdit()
        self.editor.setPlaceholderText(
            "What's on your mind?\n\n"
            "Capture today's thoughts, wins, reflections, gratitude…"
        )

        # Premium readable font for the editor
        editor_font = QFont("Georgia", 12)
        editor_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.editor.setFont(editor_font)

        # Generous line height via block format
        fmt = QTextBlockFormat()
        fmt.setLineHeight(180, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(fmt)
        self.editor.setTextCursor(cursor)

        self.editor.setStyleSheet(
            f"QTextEdit {{"
            f"  background: transparent;"
            f"  color: {_T_PRI};"
            f"  border: none;"
            f"  letter-spacing: 0.25px;"
            f"  selection-background-color: rgba(255,255,255,0.10);"
            f"  selection-color: {_T_PRI};"
            f"}}"
        )
        self.editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.editor.textChanged.connect(self._on_change)
        ew.addWidget(self.editor, 1)

        lay.addWidget(editor_wrap, 1)
        lay.addWidget(_hdiv())

        # ── Footer ─────────────────────────────────────────────────────────
        footer = QWidget()
        footer.setFixedHeight(36)
        footer.setStyleSheet(f"background: {_BG};")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(56, 0, 56, 0)
        fl.setSpacing(0)

        self.word_lbl = QLabel("0 words")
        self.word_lbl.setStyleSheet(
            f"color: {_T_TER}; font-size: 7.5pt; font-family: '{_MONO}';"
            "letter-spacing: 0.3px; background: transparent;"
        )
        fl.addWidget(self.word_lbl)

        fl.addStretch()

        # Delete link — only visible when a saved entry is loaded
        self.del_btn = QPushButton("Delete entry")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setVisible(False)
        self.del_btn.setStyleSheet(
            f"QPushButton {{ color: {_T_TER}; background: transparent; border: none;"
            f"font-size: 7.5pt; font-family: '{_MONO}'; letter-spacing: 0.3px; }}"
            f"QPushButton:hover {{ color: #7a3535; }}"
        )
        self.del_btn.clicked.connect(self.delete_requested.emit)
        fl.addWidget(self.del_btn)
        fl.addSpacing(18)

        self.status_lbl = QLabel()
        self.status_lbl.setStyleSheet(
            f"color: {_T_TER}; font-size: 7.5pt; font-family: '{_MONO}';"
            "letter-spacing: 0.3px; background: transparent;"
        )
        fl.addWidget(self.status_lbl)

        lay.addWidget(footer)

    @staticmethod
    def _arrow(glyph: str) -> QPushButton:
        btn = QPushButton(glyph)
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ color: {_T_TER}; background: transparent; border: none;"
            f"font-size: 18pt; padding: 0; }}"
            f"QPushButton:hover {{ color: {_T_PRI}; }}"
            f"QPushButton:disabled {{ color: {_T_DIM}; }}"
        )
        return btn

    # ── Internal ───────────────────────────────────────────────────────────

    def _on_change(self) -> None:
        text  = self.editor.toPlainText()
        words = len(text.split()) if text.strip() else 0
        self.word_lbl.setText(f"{words} word{'s' if words != 1 else ''}")
        self._set_status("Unsaved", dim=False)
        self.content_changed.emit(text)

    def _set_status(self, text: str, dim: bool = True) -> None:
        color = _T_TER if dim else _T_SEC
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(
            f"color: {color}; font-size: 7.5pt; font-family: '{_MONO}';"
            "letter-spacing: 0.3px; background: transparent;"
        )

    # ── Public API ─────────────────────────────────────────────────────────

    def set_date(self, d: date) -> None:
        self.date_lbl.setText(d.strftime("%A, %d %B %Y"))
        today = date.today()
        delta = (today - d).days
        if d == today:
            self.sub_lbl.setText("TODAY")
        elif delta == 1:
            self.sub_lbl.setText("YESTERDAY")
        elif 2 <= delta <= 6:
            self.sub_lbl.setText(f"{delta} DAYS AGO")
        elif d < today:
            self.sub_lbl.setText(d.strftime("%B %Y").upper())
        else:
            self.sub_lbl.setText("")

    def set_content(self, text: str, has_saved_entry: bool = False) -> None:
        """Load text without triggering the auto-save signal."""
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)

        words = len(text.split()) if text.strip() else 0
        self.word_lbl.setText(f"{words} word{'s' if words != 1 else ''}")
        self.del_btn.setVisible(has_saved_entry)
        self._set_status("Saved" if has_saved_entry else "", dim=True)

    def mark_saved(self, has_entry: bool = True) -> None:
        self._set_status("Saved", dim=True)
        self.del_btn.setVisible(has_entry)

    def mark_empty(self) -> None:
        self._set_status("", dim=True)
        self.del_btn.setVisible(False)

    def get_content(self) -> str:
        return self.editor.toPlainText()

    def focus_editor(self) -> None:
        self.editor.setFocus()
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.editor.setTextCursor(cursor)


# ── DiaryPage ──────────────────────────────────────────────────────────────────

class DiaryPage(QWidget):
    """
    Daily journal / diary page.

    ┌─ ToolBar ──────────────────────────────────────────────────────────────┐
    ├─ Sidebar ────────────┬─ Writing Pane ──────────────────────────────────┤
    │  JOURNAL             │  ‹  Wednesday, 07 June 2026            Today  › │
    │  ─────────           │  ─────────────────────────────────────────────  │
    │  JUNE 2026           │  TODAY                                          │
    │  ┌──────────────┐    │                                                 │
    │  │ 07  TODAY    │    │  What's on your mind?                           │
    │  │ JUN Snippet… │    │                                                 │
    │  └──────────────┘    │  [  large Georgia text editor              ]    │
    │  ┌──────────────┐    │  [                                         ]    │
    │  │ 06  Saturday │    │                                                 │
    │  │ JUN Yesterday│    │  ─────────────────────────────────────────────  │
    │  └──────────────┘    │  42 words          Delete entry        Saved    │
    └──────────────────────┴─────────────────────────────────────────────────┘

    Auto-saves with an 850 ms debounce after each keystroke.
    Requires the following additions to ProductivityService / models:

        DiaryEntry(id, entry_date, content)

        service.get_diary_entry(d: date) -> DiaryEntry | None
        service.list_diary_entries()     -> list[DiaryEntry]
        service.create_diary_entry(e)    -> DiaryEntry
        service.update_diary_entry(e)    -> DiaryEntry
        service.delete_diary_entry(id)   -> None
    """

    def __init__(self, service: ProductivityService) -> None:
        super().__init__()
        self.service = service
        self.setStyleSheet(f"background: {_BG};")

        self._current_date: date = date.today()

        # Debounced auto-save
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(_AUTOSAVE_MS)
        self._save_timer.timeout.connect(self._do_save)

        self._build_ui()
        self._nav_to(date.today())

    # ── UI skeleton ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Body
        body = QWidget()
        body.setStyleSheet(f"background: {_BG};")
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self._sidebar = _Sidebar()
        self._sidebar.date_selected.connect(self._nav_to)
        bl.addWidget(self._sidebar)
        bl.addWidget(_vdiv())

        self._pane = _WritingPane()
        self._pane.prev_btn.clicked.connect(self._prev_day)
        self._pane.next_btn.clicked.connect(self._next_day)
        self._pane.today_btn.clicked.connect(lambda: self._nav_to(date.today()))
        self._pane.content_changed.connect(self._on_content_changed)
        self._pane.delete_requested.connect(self._delete_entry)
        bl.addWidget(self._pane, 1)

        root.addWidget(body, 1)

    # ── Day navigation ────────────────────────────────────────────────────

    def _prev_day(self) -> None:
        self._nav_to(self._current_date - timedelta(days=1))

    def _next_day(self) -> None:
        target = self._current_date + timedelta(days=1)
        if target <= date.today():
            self._nav_to(target)

    def _nav_to(self, d: date) -> None:
        # Flush any pending save before leaving the current date
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._do_save()

        self._current_date = d

        # Load entry (or blank if none saved yet)
        entry = self.service.get_diary_entry(d)
        self._pane.set_date(d)
        self._pane.set_content(
            entry.content if entry else "",
            has_saved_entry=(entry is not None),
        )

        # Disable next arrow on today
        self._pane.next_btn.setEnabled(d < date.today())

        self._refresh_sidebar()

    def _refresh_sidebar(self) -> None:
        entries = self.service.list_diary_entries()
        self._sidebar.populate(entries, selected_date=self._current_date)

    # ── Auto-save ──────────────────────────────────────────────────────────

    def _on_content_changed(self, _: str) -> None:
        """Restart the debounce timer on every keystroke."""
        self._save_timer.start()

    def _do_save(self) -> None:
        content = self._pane.get_content()
        if not content.strip():
            return   # never persist empty entries

        entry = self.service.get_diary_entry(self._current_date)
        if entry:
            entry.content = content
            self.service.update_diary_entry(entry)
        else:
            self.service.create_diary_entry(
                DiaryEntry(id=None, entry_date=self._current_date, content=content)
            )

        self._pane.mark_saved(has_entry=True)
        self._refresh_sidebar()

    # ── Delete ────────────────────────────────────────────────────────────

    def _delete_entry(self) -> None:
        entry = self.service.get_diary_entry(self._current_date)
        if entry and entry.id is not None:
            self.service.delete_diary_entry(entry.id)
            self._pane.set_content("", has_saved_entry=False)
            self._pane.mark_empty()
            self._refresh_sidebar()

    # ── Toolbar shortcut ──────────────────────────────────────────────────

    def _open_today(self) -> None:
        self._nav_to(date.today())
        self._pane.focus_editor()

    # ── External refresh (called by app shell on tab switch) ───────────────

    def refresh(self) -> None:
        self._refresh_sidebar()