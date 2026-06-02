from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt, QEvent, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QFontDatabase, QPixmap, QIcon, QPalette
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QLineEdit,
    QTextEdit,
    QWidget,
)

from ..core.models import Habit
from ..core.services import ProductivityService
from .toolbar import ToolBar

# ─────────────────────────── palette ────────────────────────────────────────
_BG         = "#111111"
_SURF       = "#111113"
_BORDER_DIM = "rgba(255,255,255,0.06)"
_BORDER_MID = "rgba(255,255,255,0.10)"
_T_PRI      = "#e8e8ed"
_T_SEC      = "#636366"
_T_TER      = "#2e2e30"

# ─────────────────────────── geometry ───────────────────────────────────────
_COL_W    = 76      # px per day column
_LEFT_W   = 256     # habit name column width
_HDR_H    = 56      # day-header row height
_ROW_H    = 70      # habit row height
_CIRCLE_D = 30      # day dot diameter (reduced)
_AVATAR_D = 30      # avatar circle diameter


# ─────────────────────────────────────────────────────────────────────────────
#  Primitives
# ─────────────────────────────────────────────────────────────────────────────

class _HDiv(QFrame):
    """1 px horizontal rule."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {_BORDER_DIM}; border: none;")


class _Avatar(QWidget):
    """Filled circle showing one initial letter."""
    def __init__(self, letter: str, parent=None):
        super().__init__(parent)
        self.letter = (letter.upper())[:1]
        self.setFixedSize(_AVATAR_D, _AVATAR_D)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#242426"))
        p.drawEllipse(r)
        p.setPen(QColor("#8e8e93"))
        f = QFont()
        f.setPointSize(9)
        f.setWeight(QFont.Weight.Medium)
        p.setFont(f)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.letter)
        p.end()


class _Dot(QWidget):
    """
    Single-day completion circle.
      • active   → solid light-grey fill + dark tick
      • inactive → subtle outlined circle
    """
    def __init__(self, active: bool = False, is_today: bool = False,
                 interactive: bool = True,
                 toggle_callback: callable | None = None,
                 parent=None):
        super().__init__(parent)
        self.active          = active
        self.is_today        = is_today
        self.interactive     = interactive
        self.toggle_callback = toggle_callback
        self._hovered        = False
        self.setFixedSize(_CIRCLE_D, _CIRCLE_D)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        if interactive:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, _event):
        self._hovered = True
        self.update()

    def leaveEvent(self, _event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, e):
        if self.interactive and e.button() == Qt.MouseButton.LeftButton:
            self.active = not self.active
            self.update()
            if self.toggle_callback:
                self.toggle_callback(self.active)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(3, 3, -3, -3)

        if self.active:
            # ── active: draw white tick only (no filled background) ──
            p.setBrush(Qt.BrushStyle.NoBrush)
            pen = QPen(QColor("#ffffff"))
            pen.setWidth(3 if self._hovered else 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            x, y, w, h = r.x(), r.y(), r.width(), r.height()
            # smaller tick proportions to avoid filling the circle
            p.drawLine(int(x + w * .34), int(y + h * .58),
                       int(x + w * .50), int(y + h * .74))
            p.drawLine(int(x + w * .50), int(y + h * .74),
                       int(x + w * .73), int(y + h * .38))
        else:
            # ── outlined: dim border, near-transparent fill ──
            border = "#484848" if self.is_today else "#323234"
            if self._hovered:
                border = "#e8e8ed"
            pen = QPen(QColor(border))
            pen.setWidth(1)
            p.setPen(pen)
            p.setBrush(QColor(255, 255, 255, 12) if self._hovered else QColor(255, 255, 255, 5))
            p.drawEllipse(r)

        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  Compound rows
# ─────────────────────────────────────────────────────────────────────────────

class _DayHeader(QWidget):
    """Row of day abbreviation + date number columns."""

    def __init__(self, days: list[tuple[str, str, date]],
                 today_col: int = -1, parent=None):
        super().__init__(parent)
        self.setFixedHeight(_HDR_H)
        self.setStyleSheet("background: transparent;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(28, 0, 28, 0)
        lay.setSpacing(0)

        # placeholder for name column
        sp = QWidget()
        sp.setFixedWidth(_LEFT_W)
        sp.setStyleSheet("background: transparent;")
        lay.addWidget(sp)

        for i, (abbr, num, _d) in enumerate(days):
            is_t = (i == today_col)

            col = QWidget()
            col.setFixedWidth(_COL_W)
            col.setStyleSheet("background: transparent;")
            cl = QVBoxLayout(col)
            cl.setContentsMargins(0, 10, 0, 10)
            cl.setSpacing(3)

            abbr_lbl = QLabel(abbr)
            abbr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            abbr_lbl.setStyleSheet(
                f"color: {_T_PRI if is_t else _T_SEC};"
                f"font-size: 7.5pt; letter-spacing: 0.9px;"
                f"font-weight: {'600' if is_t else '400'};"
                "background: transparent;"
            )

            num_lbl = QLabel(num)
            num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num_lbl.setStyleSheet(
                f"color: {_T_PRI if is_t else _T_TER};"
                f"font-size: 9.5pt;"
                f"font-weight: {'600' if is_t else '400'};"
                "background: transparent;"
            )

            cl.addWidget(abbr_lbl)
            cl.addWidget(num_lbl)
            lay.addWidget(col)

        lay.addStretch(1)


class _HabitRow(QWidget):
    """Single habit row: avatar + name + 7 dots."""

    def __init__(self, title: str, days: list[bool], day_dates: list[date],
                 today_col: int = -1,
                 toggle_callback: callable | None = None,
                 habit_id: int | None = None,
                 parent=None,
                 parent_page=None):
        super().__init__(parent)
        self.setObjectName("HabitRow")
        self.setFixedHeight(_ROW_H)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.habit_id = habit_id
        self.parent_page = parent_page
        self._ns = "QWidget#HabitRow { background: transparent; }"
        self._hs = "QWidget#HabitRow { background: rgba(255,255,255,0.022); }"
        self.setStyleSheet(self._ns)
        self.installEventFilter(self)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(28, 0, 28, 0)
        lay.setSpacing(0)

        # ── name section ──────────────────────────────────────────────────
        name_w = QWidget()
        name_w.setFixedWidth(_LEFT_W)
        name_w.setStyleSheet("background: transparent;")
        nl = QHBoxLayout(name_w)
        nl.setContentsMargins(0, 0, 16, 0)
        nl.setSpacing(12)
        nl.addWidget(_Avatar(title[0] if title else "?"),
                     alignment=Qt.AlignmentFlag.AlignVCenter)
        name_lbl = QLabel(title)
        name_lbl.setStyleSheet(
            f"color: {_T_PRI}; font-size: 10.5pt; font-weight: 500; background: transparent;"
        )
        nl.addWidget(name_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
        nl.addStretch()
        lay.addWidget(name_w)

        # ── dots ──────────────────────────────────────────────────────────
        for i, active in enumerate(days):
            cell = QWidget()
            cell.setFixedWidth(_COL_W)
            cell.setStyleSheet("background: transparent;")
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(0, 0, 0, 0)
            day_date = day_dates[i]
            cl.addWidget(
                _Dot(
                    active,
                    is_today=(i == today_col),
                    interactive=True,
                    toggle_callback=(
                        lambda active, day=day_date: toggle_callback(day, active)
                        if toggle_callback else None
                    ),
                ),
                alignment=Qt.AlignmentFlag.AlignCenter
            )
            lay.addWidget(cell)

        lay.addStretch(1)

    def enterEvent(self, _e):
        self.setStyleSheet(self._hs)

    def leaveEvent(self, _e):
        self.setStyleSheet(self._ns)

    def eventFilter(self, obj, event):
        if obj is self:
            if event.type() == QEvent.Type.MouseButtonDblClick:
                if self.habit_id is not None and self.parent_page and hasattr(self.parent_page, "edit_habit"):
                    self.parent_page.edit_habit(self.habit_id)
        return super().eventFilter(obj, event)


# ─────────────────────────────────────────────────────────────────────────────
#  Form Dialog
# ─────────────────────────────────────────────────────────────────────────────

class HabitFormDialog(QDialog):
    def __init__(self, parent=None, habit: Habit | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Habit Details" if habit else "Create Habit")
        self.resize(500, 200)
        self.original_habit = habit
        self._build_ui()
        if habit:
            self._load_habit(habit)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_card = QWidget()
        form = QFormLayout(form_card)

        self.title = QLineEdit()
        self.description = QTextEdit()
        self.description.setMaximumHeight(80)

        form.addRow("Title", self.title)
        form.addRow("Description", self.description)
        
        # Action buttons row aligned to the right, at the top of the dialog
        actions_container = QWidget()
        actions_layout = QHBoxLayout(actions_container)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.addStretch(1)

        self.save_btn = QPushButton()
        self.save_btn.setIcon(self._create_icon("save"))
        self.save_btn.setToolTip("Save")
        self.save_btn.setIconSize(QSize(20, 20))
        self.save_btn.setFixedSize(36, 36)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #ffffff; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); border-radius: 10px; }"
        )
        self.save_btn.clicked.connect(self.accept)
        actions_layout.addWidget(self.save_btn)

        if self.original_habit:
            self.delete_btn = QPushButton()
            self.delete_btn.setIcon(self._create_icon("delete"))
            self.delete_btn.setToolTip("Delete")
            self.delete_btn.setIconSize(QSize(20, 20))
            self.delete_btn.setFixedSize(36, 36)
            self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.delete_btn.setStyleSheet(
                "QPushButton { background: transparent; border: none; color: #ffffff; }"
                "QPushButton:hover { background: rgba(255,255,255,0.08); border-radius: 10px; }"
            )
            self.delete_btn.clicked.connect(self.on_delete_clicked)
            actions_layout.addWidget(self.delete_btn)

        scroll.setWidget(form_card)
        layout.addWidget(scroll)
        layout.addWidget(actions_container)
    
    def on_delete_clicked(self) -> None:
        self.delete_confirmed = True
        self.accept()

    def _create_icon(self, kind: str) -> QIcon:
        pix = QPixmap(24, 24)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#ffffff"))
        pen.setWidth(2)
        painter.setPen(pen)

        if kind == "save":
            painter.drawRect(5, 5, 14, 14)
            painter.drawRect(5, 5, 14, 9)
            painter.drawLine(9, 13, 9, 17)
            painter.drawLine(15, 13, 15, 17)
        elif kind == "cancel":
            painter.drawLine(7, 7, 17, 17)
            painter.drawLine(17, 7, 7, 17)
        elif kind == "delete":
            painter.drawLine(7, 8, 17, 8)
            painter.drawLine(9, 8, 9, 18)
            painter.drawLine(15, 8, 15, 18)
            painter.drawLine(7, 18, 17, 18)
            painter.drawLine(7, 8, 17, 8)
            painter.drawLine(9, 8, 15, 8)
            painter.drawLine(7, 8, 8, 6)
            painter.drawLine(17, 8, 16, 6)
        painter.end()
        return QIcon(pix)

    def _load_habit(self, habit: Habit) -> None:
        self.title.setText(habit.title)
        self.description.setPlainText(habit.description)

    def is_delete_requested(self) -> bool:
        return getattr(self, "delete_confirmed", False)

    def get_habit_data(self) -> Habit:
        return Habit(
            title=self.title.text().strip() or "Untitled habit",
            description=self.description.toPlainText().strip(),
            id=self.original_habit.id if self.original_habit else None
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Page
# ─────────────────────────────────────────────────────────────────────────────

class HabitPage(QWidget):

    # Sample data — replace with real persistence
    _HABITS = [
        {"title": "Do gekks ...",    "days": [True,  True,  False, False, False, False, False]},
        {"title": "Read 15 min",     "days": [True,  False, True,  True,  False, False, False]},
        {"title": "Morning workout", "days": [False, True,  True,  False, False, False, False]},
        {"title": "Meditate",        "days": [True,  True,  True,  False, False, False, False]},
    ]

    def __init__(self, service: ProductivityService) -> None:
        super().__init__()
        self.service = service
        self.week_offset = 0
        self.setStyleSheet(f"background: {_BG};")
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(_BG))
        self.setPalette(palette)
        self._background_palette = palette
        
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Toolbar stays at top
        self.toolbar = ToolBar(self)
        self.toolbar.add_button.clicked.connect(self.add_habit)
        root.addWidget(self.toolbar)
        
        # Container for renderable content (nav + scroll area)
        self._content_container = QWidget()
        self._content_container.setStyleSheet(f"background: {_BG};")
        self._content_container.setAutoFillBackground(True)
        self._content_container.setPalette(palette)
        self._root = QVBoxLayout(self._content_container)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)
        root.addWidget(self._content_container, 1)
        
        self._render()

    def refresh(self) -> None:
        self._render()

    def _load_habits(self) -> list[Habit]:
        habits = self.service.habits.list()
        if not habits:
            self._seed_default_habits()
            habits = self.service.habits.list()
        return habits

    def _seed_default_habits(self) -> None:
        days = self._week_days()
        day_dates = [d for _, _, d in days]
        for sample in self._HABITS:
            habit = Habit(title=sample["title"], description="")
            habit_id = self.service.create_habit(habit)
            for completed, completion_date in zip(sample["days"], day_dates):
                if completed:
                    self.service.habits.mark_completed(habit_id, completion_date)

    def _toggle_completion(self, habit_id: int, completion_date: date, active: bool) -> None:
        if active:
            self.service.habits.mark_completed(habit_id, completion_date)
        else:
            self.service.habits.unmark_completed(habit_id, completion_date)
        self._render()

    # ─────────────────────────────────────────────────────────────────────

    def _week_days(self) -> list[tuple[str, str, date]]:
        """Return 7 (abbr, zero-padded-day, date) tuples starting on Wednesday."""
        today = date.today()
        delta = (today.weekday() - 2) % 7          # anchor on Wednesday
        start = (today - timedelta(days=delta)
                 + timedelta(weeks=self.week_offset))
        return [
            (
                (start + timedelta(days=i)).strftime("%a").upper(),
                f"{(start + timedelta(days=i)).day:02d}",
                start + timedelta(days=i),
            )
            for i in range(7)
        ]

    def _render(self) -> None:
        # ── wipe ──────────────────────────────────────────────────────────
        # Prevent intermediate repaints while we rebuild the content
        self.setUpdatesEnabled(False)
        if hasattr(self, '_content_container') and self._content_container:
            self._content_container.setUpdatesEnabled(False)
        while self._root.count():
            item = self._root.takeAt(0)
            if w := item.widget():
                w.deleteLater()

        days    = self._week_days()
        today   = date.today()
        today_i = next((i for i, (*_, d) in enumerate(days) if d == today), -1)
        s, e    = days[0][2], days[-1][2]
        s_str   = f"{s.day} {s.strftime('%b')}" if s.month != e.month else str(s.day)
        range_s = f"{s_str} – {e.day} {e.strftime('%b')}"
        habits  = self._load_habits()

        # ── navigation bar ────────────────────────────────────────────────
        nav = QWidget()
        nav.setObjectName("NavBar")
        nav.setFixedHeight(56)
        nav.setStyleSheet(f"QWidget#NavBar {{ background: {_BG}; }}")
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(32, 0, 32, 0)
        nl.setSpacing(0)

        nl.addStretch(1)

        prev_btn = self._nav_arrow("‹")
        prev_btn.clicked.connect(lambda: self._jump(-1))
        nl.addWidget(prev_btn)

        wlbl = QLabel(range_s)
        wlbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wlbl.setStyleSheet(
            f"color: {_T_PRI}; font-size: 11pt; font-weight: 500;"
            "padding: 0 32px; background: transparent;"
        )
        nl.addWidget(wlbl)

        next_btn = self._nav_arrow("›")
        next_btn.clicked.connect(lambda: self._jump(1))
        nl.addWidget(next_btn)

        nl.addSpacing(28)

        today_btn = QPushButton("Today")
        today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        today_btn.setStyleSheet(
            f"QPushButton {{ color: {_T_SEC}; background-color: transparent; border: none; "
            f"font-size: 9.5pt; padding: 0; }} "
            f"QPushButton:hover {{ color: {_T_PRI}; }}"
        )
        today_btn.clicked.connect(self._to_today)
        nl.addWidget(today_btn)

        nl.addStretch(1)

        self._root.addWidget(nav)
        self._root.addWidget(_HDiv())

        # ── scrollable body ───────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {_BG}; border: none; }}"
            f"QScrollArea > QWidget {{ background: transparent; }}"
            f"QScrollBar:vertical, QScrollBar:horizontal {{ background: transparent; }}"
            f"QScrollBar::handle {{ background: rgba(255,255,255,0.04); border-radius: 6px; }}"
            f"QScrollBar::add-line, QScrollBar::sub-line {{ background: transparent; }}"
        )
        scroll.setAutoFillBackground(True)
        scroll.setPalette(self._background_palette)
        scroll.viewport().setAutoFillBackground(True)
        scroll.viewport().setPalette(self._background_palette)
        scroll.viewport().setStyleSheet(f"background: {_BG};")

        body = QWidget()
        body.setObjectName("Body")
        body.setStyleSheet(f"QWidget#Body {{ background: {_BG}; min-height: 100%; }}")
        body.setAutoFillBackground(True)
        body.setPalette(self._background_palette)
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        # Centered wrapper containing header and habits
        habits_wrapper = QWidget()
        habits_wrapper.setStyleSheet("background: transparent;")
        habits_layout = QVBoxLayout(habits_wrapper)
        habits_layout.setContentsMargins(0, 0, 0, 0)
        habits_layout.setSpacing(0)

        habits_layout.addWidget(_DayHeader(days, today_col=today_i))
        habits_layout.addWidget(_HDiv())

        day_dates = [d for _, _, d in days]
        for habit in habits:
            completions = self.service.habits.get_completions(habit.id, s, e) if habit.id is not None else set()
            habits_layout.addWidget(
                _HabitRow(
                    habit.title,
                    [d in completions for d in day_dates],
                    day_dates,
                    today_col=today_i,
                    toggle_callback=lambda date_, active, habit_id=habit.id: self._toggle_completion(habit_id, date_, active),
                    habit_id=habit.id,
                    parent=self,
                    parent_page=self,
                )
            )
            habits_layout.addWidget(_HDiv())

        habits_layout.addStretch(1)

        # Center the entire content wrapper
        center_layout = QHBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addStretch(1)
        center_layout.addWidget(habits_wrapper)
        center_layout.addStretch(1)
        bl.addLayout(center_layout, 1)

        scroll.setWidget(body)
        self._root.addWidget(scroll, 1)
        # Re-enable updates and force a repaint after rebuilding
        if hasattr(self, '_content_container') and self._content_container:
            self._content_container.setUpdatesEnabled(True)
        self.setUpdatesEnabled(True)
        self.update()

    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _nav_arrow(glyph: str) -> QPushButton:
        btn = QPushButton(glyph)
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ color: {_T_SEC}; background-color: transparent; border: none; "
            "font-size: 20pt; padding: 0; } "
            f"QPushButton:hover {{ color: {_T_PRI}; }}"
        )
        return btn

    def _jump(self, delta: int) -> None:
        self.week_offset += delta
        self._render()

    def _to_today(self) -> None:
        self.week_offset = 0
        self._render()

    def add_habit(self) -> None:
        """Add a new habit. Called by toolbar button."""
        dialog = HabitFormDialog(self)
        if dialog.exec() == QDialog.Accepted:
            habit_data = dialog.get_habit_data()
            self.service.create_habit(habit_data)
            self.refresh()

    def edit_habit(self, habit_id: int | None = None) -> None:
        """Edit an existing habit. Called by double-click."""
        if habit_id is None:
            return
        habit = self.service.habits.get(habit_id)
        if not habit:
            return
        dialog = HabitFormDialog(self, habit)
        if dialog.exec() == QDialog.Accepted:
            if dialog.is_delete_requested():
                self.delete_habit(habit_id)
            else:
                updated_habit = dialog.get_habit_data()
                self.service.update_habit(habit_id, updated_habit)
                self.refresh()

    def delete_habit(self, habit_id: int) -> None:
        """Delete a habit."""
        self.service.delete_habit(habit_id)
        self.refresh()