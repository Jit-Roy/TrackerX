from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt, QRectF, QSize, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.models import WeeklyGoalEntry, WeeklyPlan
from core.services import ProductivityService
from .helper.icons import build_orbit_icon


# ── Palette ────────────────────────────────────────────────────────────────────
_BG             = "#0d0d0d"
_CARD_BG        = "#141414"
_CARD_BG_TODAY  = "#1c1c1c"
_BORDER         = "rgba(255,255,255,0.06)"
_BORDER_TODAY   = "rgba(255,255,255,0.20)"
_ACCENT         = "#d0d0d0"
_ACCENT_HOVER   = "#f0f0f0"
_ACCENT_DIM     = "rgba(255,255,255,0.08)"
_TEXT_PRI       = "#e8e8ed"
_TEXT_SEC       = "#8e8e93"
_TEXT_MUT       = "#48484a"
_BTN_BG         = "rgba(255,255,255,0.05)"
_SEP            = "rgba(255,255,255,0.07)"
_NOTE_BG        = "rgba(255,255,255,0.03)"
_DAY_WIDTH      = 300


# ── Fix 1: Custom circle checkbox that paints a real tick ──────────────────────
class _CircleCheck(QWidget):
    """
    A fully custom-painted circular checkbox.

    • Unchecked  → empty circle with a coloured border
    • Checked    → filled accent circle with a crisp white tick mark
    """
    toggled = Signal(bool)

    def __init__(
        self,
        checked: bool = False,
        is_today: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._checked  = checked
        self._is_today = is_today
        self._hovered  = False
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    # ── Public helpers ─────────────────────────────────────────────────────────
    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, val: bool) -> None:
        if self._checked != val:
            self._checked = val
            self.update()

    # ── Events ─────────────────────────────────────────────────────────────────
    def mousePressEvent(self, _event) -> None:
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        self.update()

    def enterEvent(self, _event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, _event) -> None:
        self._hovered = False
        self.update()

    # ── Paint ──────────────────────────────────────────────────────────────────
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect   = QRectF(1.5, 1.5, 15, 15)
        accent = QColor(_ACCENT)

        # Border-only circle
        ring_color = accent if self._is_today else QColor("#444444")
        if self._hovered:
            ring_color = accent

        p.setBrush(
            QBrush(QColor(200, 200, 200, 40)) if self._hovered and not self._checked
            else Qt.BrushStyle.NoBrush
        )
        p.setPen(QPen(ring_color, 1.5))
        p.drawEllipse(rect)

        if self._checked:
            # White (accent) tick mark
            tick_pen = QPen(
                accent, 1.8,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
            p.setPen(tick_pen)
            path = QPainterPath()
            # coords tuned for an 18×18 cell
            path.moveTo(4.5, 9.2)
            path.lineTo(7.5, 12.2)
            path.lineTo(13.0, 5.8)
            p.drawPath(path)

        p.end()


# ── Fix 2: Custom + button that always paints a centred plus sign ──────────────
class _PlusButton(QWidget):
    """
    A circular button that draws its own '+' via QPainter so the glyph
    is always centred regardless of platform font metrics.
    """
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hovered = False
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def enterEvent(self, _event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, _event) -> None:
        self._hovered = False
        self.update()

    def mousePressEvent(self, _event) -> None:
        self.clicked.emit()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Circle background
        bg_alpha = 60 if self._hovered else 25
        p.setBrush(QBrush(QColor(255, 255, 255, bg_alpha)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(0, 0, 24, 24))

        # Plus sign
        plus_color = QColor(_ACCENT) if self._hovered else QColor(_TEXT_PRI)
        pen = QPen(plus_color, 1.8, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        cx, cy, arm = 12.0, 12.0, 5.0
        p.drawLine(QRectF(cx - arm, cy, arm * 2, 0).topLeft(),
                   QRectF(cx - arm, cy, arm * 2, 0).topRight())
        p.drawLine(QRectF(cx, cy - arm, 0, arm * 2).topLeft(),
                   QRectF(cx, cy - arm, 0, arm * 2).bottomLeft())

        p.end()


# ── Goal row ───────────────────────────────────────────────────────────────────
class _GoalRow(QWidget):
    def __init__(
        self,
        entry: WeeklyGoalEntry,
        parent_page=None,
        is_today: bool = False,
    ) -> None:
        super().__init__(parent_page)
        self.entry = entry
        self.parent_page = parent_page
        self.is_today = is_today
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._build()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 3, 0, 3)
        lay.setSpacing(8)

        done = self.entry.completed

        # ── Use the custom circle checkbox ────────────────────────────────────
        self.cb = _CircleCheck(checked=done, is_today=self.is_today)
        self.cb.toggled.connect(self._toggle)
        lay.addWidget(self.cb, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.lbl = QLineEdit(self.entry.title or "New goal")
        self.lbl.setReadOnly(True)
        self.lbl.setStyleSheet(
            f"QLineEdit {{ color: {(_TEXT_MUT if done else _TEXT_PRI)}; font-size: 10pt; "
            f"background: transparent; border: none; letter-spacing: 0.1px;"
            + ("; text-decoration: line-through;" if done else "")
            + f"}} QLineEdit:focus {{ border: 1px solid {_BORDER_TODAY}; border-radius: 4px; background: #222222; text-decoration: none; }}"
        )
        self.lbl.returnPressed.connect(self._save_edit)
        lay.addWidget(self.lbl, 1)

        # edit button
        edit_btn = QPushButton("✎")
        edit_btn.setFixedSize(18, 18)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_TEXT_MUT}; border: none; font-size: 8pt; }}"
            f"QPushButton:hover {{ color: {_TEXT_SEC}; }}"
        )
        edit_btn.clicked.connect(self._edit)
        lay.addWidget(edit_btn)

        # delete button uses the same simple white icon style as habit page
        delete_btn = QPushButton()
        delete_btn.setIcon(self._create_icon("delete"))
        delete_btn.setToolTip("Delete")
        delete_btn.setIconSize(QSize(16, 16))
        delete_btn.setFixedSize(24, 24)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #ffffff; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); border-radius: 10px; }"
        )
        delete_btn.clicked.connect(self._delete)
        lay.addWidget(delete_btn)

        self.setStyleSheet("QWidget { background: transparent; }")

    def _toggle(self, checked: bool) -> None:
        if self.entry.id and self.parent_page:
            self.parent_page.toggle_goal_completion(self.entry.id, checked)

    def _create_icon(self, kind: str) -> QIcon:
        pix = QPixmap(24, 24)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#ffffff"))
        pen.setWidth(2)
        painter.setPen(pen)

        if kind == "delete":
            painter.drawLine(7, 8, 17, 18)
            painter.drawLine(17, 8, 7, 18)
        painter.end()
        return QIcon(pix)

    def _edit(self) -> None:
        self.lbl.setReadOnly(False)
        self.lbl.setFocus()
        self.lbl.selectAll()
        
    def _save_edit(self) -> None:
        self.lbl.setReadOnly(True)
        self.lbl.clearFocus()
        if self.entry.id and self.parent_page:
            self.entry.title = self.lbl.text().strip() or "Untitled goal"
            self.parent_page.service.update_weekly_goal_entry(self.entry.id, self.entry)
            self.parent_page.refresh()

    def _delete(self) -> None:
        if self.entry.id and self.parent_page:
            self.parent_page.delete_goal(self.entry.id)


# ── Custom Scroll Area ────────────────────────────────────────────────────────
class _PlannerScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._target_day_index = None

    def center_on_day(self, day_index: int):
        self._target_day_index = day_index
        # Defer the center calculation until the event loop is idle.
        # This guarantees that all intermediate layout sizes are resolved.
        QTimer.singleShot(0, self._safe_do_center)

    def _safe_do_center(self):
        try:
            # If the C++ object was deleted due to rapid tab switching, this raises RuntimeError
            _ = self.viewport()
        except RuntimeError:
            return
        self._do_center()

    def _do_center(self):
        if self._target_day_index is None:
            return
        bar = self.horizontalScrollBar()
        
        if bar.maximum() > 0:
            viewport_width = self.viewport().width()
            card_width = _DAY_WIDTH
            card_spacing = 10
            left_margin = 28
            x_center = left_margin + self._target_day_index * (card_width + card_spacing) + card_width / 2
            target = int(x_center - viewport_width / 2)
            bar.setValue(max(0, min(target, bar.maximum())))
            self._target_day_index = None


# ── Planner page ───────────────────────────────────────────────────────────────
class PlannerPage(QWidget):
    def __init__(self, service: ProductivityService) -> None:
        super().__init__()
        self.service = service
        self.week_offset = 0
        self._day_notes: dict[int, str] = {}
        self._inline_inputs: dict[int, QLineEdit] = {}
        self._needs_center = False
        self.setStyleSheet(f"background: {_BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.content = QWidget()
        self.content.setStyleSheet(f"background: {_BG};")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        root.addWidget(self.content, 1)

        self._render()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._needs_center = True
        self._to_today()

    # ── Public ─────────────────────────────────────────────────────────────────
    def refresh(self) -> None:
        self._render()

    def on_navigated_to(self) -> None:
        self._to_today()

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _week_days(self) -> list[tuple[str, str, date]]:
        today = date.today()
        start = today + timedelta(days=(7 * self.week_offset) - today.weekday())
        return [
            (d.strftime("%a").upper(), d.strftime("%d %b"), d)
            for d in (start + timedelta(days=i) for i in range(7))
        ]

    @staticmethod
    def _arrow(label: str, callback) -> QPushButton:
        btn = QPushButton(label)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ color: {_TEXT_SEC}; background: transparent; "
            f"border: none; outline: none; font-size: 16pt; padding: 0; }}"
            f"QPushButton:hover {{ color: {_TEXT_PRI}; }}"
        )
        btn.clicked.connect(callback)
        return btn

    def _save_note(self, plan_id: int, day_of_week: int, text: str) -> None:
        self._day_notes[day_of_week] = text
        self.service.save_weekly_plan_note(plan_id, day_of_week, text)

    # ── Render ─────────────────────────────────────────────────────────────────
    def _render(self, reset_scroll: bool = False) -> None:
        saved_scroll = None
        if not reset_scroll and hasattr(self, '_scroll_area') and self._scroll_area:
            saved_scroll = self._scroll_area.horizontalScrollBar().value()

        self.setUpdatesEnabled(False)
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if w := item.widget():
                w.deleteLater()

        today     = date.today()
        days      = self._week_days()
        today_index = next(
            (idx for idx, (_, _, d) in enumerate(days) if d == today),
            None,
        )
        plan      = self.service.get_or_create_weekly_plan(days[0][2])

        self._day_notes = {}
        if plan and plan.id is not None:
            self._day_notes = self.service.get_weekly_plan_notes(plan.id)

        sep0 = QFrame()
        sep0.setFrameShape(QFrame.Shape.HLine)
        sep0.setStyleSheet(f"background: {_BORDER}; border: none; max-height: 1px;")
        self.content_layout.addWidget(sep0)

        # ── Navigation row ────────────────────────────────────────────────────
        s, e = days[0][2], days[-1][2]
        rng  = f"{s.day} – {e.day} {e.strftime('%b %Y')}"

        nav = QWidget()
        nav.setFixedHeight(50)
        nav.setStyleSheet(f"background: {_BG};")
        n_lay = QHBoxLayout(nav)
        n_lay.setContentsMargins(36, 0, 36, 0)
        n_lay.setSpacing(0)

        n_lay.addStretch(1)
        n_lay.addWidget(self._arrow("‹", lambda: self._jump(-1)))
        n_lay.addSpacing(16)

        rng_lbl = QLabel(rng)
        rng_lbl.setStyleSheet(
            f"color: {_TEXT_PRI}; font-size: 12pt; font-weight: 600; background: transparent;"
        )
        n_lay.addWidget(rng_lbl)
        n_lay.addSpacing(16)
        n_lay.addWidget(self._arrow("›", lambda: self._jump(1)))
        n_lay.addSpacing(18)

        today_btn = QPushButton("Today")
        today_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        def _update_today_highlight(*args) -> None:
            color = _TEXT_SEC
            if today_index is not None and hasattr(self, '_scroll_area'):
                bar = self._scroll_area.horizontalScrollBar()
                vw = self._scroll_area.viewport().width()
                if vw > 0:
                    x_center = 28 + today_index * 310 + 150
                    target_val = int(x_center - vw / 2)
                    target_val = max(0, min(target_val, bar.maximum()))
                    
                    # Highlight only if the scrollbar is within 150px (half a card) of the ideal Today position
                    if abs(bar.value() - target_val) < 150:
                        color = _TEXT_PRI
                else:
                    color = _TEXT_PRI
            today_btn.setStyleSheet(
                f"QPushButton {{ color: {color}; background: transparent; border: none; outline: none; font-size: 9.5pt; }}"
                f"QPushButton:hover {{ color: {_TEXT_PRI}; }}"
            )

        # Initialize its style
        _update_today_highlight()

        today_btn.clicked.connect(self._to_today)
        n_lay.addWidget(today_btn)
        n_lay.addStretch(1)
        self.content_layout.addWidget(nav)

        # ── Day cards ─────────────────────────────────────────────────────────
        scroll = _PlannerScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:horizontal { height: 5px; background: transparent; margin: 0; }"
            "QScrollBar::handle:horizontal { background: rgba(255,255,255,0.10); border-radius: 2px; min-width: 30px; }"
            "QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }"
            "QScrollBar:vertical { width: 5px; background: transparent; margin: 0; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.10); border-radius: 2px; }"
        )

        body = QWidget()
        body.setStyleSheet(f"background: {_BG};")
        b_lay = QHBoxLayout(body)
        b_lay.setContentsMargins(28, 8, 28, 12)
        b_lay.setSpacing(10)

        entries_by_day: dict[int, list[WeeklyGoalEntry]] = {i: [] for i in range(7)}
        for entry in plan.entries:
            entries_by_day[entry.day_of_week].append(entry)

        for day_idx, (abbr, date_str, day_date) in enumerate(days):
            is_today = (day_date == today)
            day_ents = entries_by_day[day_idx]

            card_bg     = _CARD_BG_TODAY if is_today else _CARD_BG
            border_col  = _BORDER_TODAY  if is_today else _BORDER
            hdr_color   = _TEXT_PRI      if is_today else _TEXT_PRI
            sub_color   = _ACCENT        if is_today else _TEXT_SEC

            card = QFrame()
            card.setObjectName("DayCard")
            card.setFixedWidth(_DAY_WIDTH)
            card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
            card.setStyleSheet(
                f"QFrame#DayCard {{ background: {card_bg}; border: 1px solid {border_col}; border-radius: 16px; }}"
            )

            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(14, 14, 14, 14)
            c_lay.setSpacing(0)

            # Day header row
            hdr_row = QWidget()
            hdr_row.setStyleSheet("background: transparent;")
            hr_lay = QHBoxLayout(hdr_row)
            hr_lay.setContentsMargins(0, 0, 0, 0)
            hr_lay.setSpacing(0)

            abbr_lbl = QLabel(abbr)
            abbr_lbl.setStyleSheet(
                f"color: {hdr_color}; font-size: 9pt; font-weight: 700; "
                f"letter-spacing: 1.5px; background: transparent;"
            )
            hr_lay.addWidget(abbr_lbl)
            hr_lay.addStretch(1)

            # Custom _PlusButton
            plus_btn = _PlusButton()
            plus_btn.clicked.connect(lambda d=day_idx: self._show_inline_input(d))
            hr_lay.addWidget(plus_btn)

            c_lay.addWidget(hdr_row)
            


            date_lbl = QLabel(date_str)
            date_lbl.setStyleSheet(
                f"color: {sub_color}; font-size: 10pt; font-weight: {'600' if is_today else '400'}; "
                f"background: transparent; margin-top: 1px;"
            )
            c_lay.addWidget(date_lbl)
            c_lay.addSpacing(10)

            goals_section = QLabel("Goals")
            goals_section.setStyleSheet(
                f"color: {_TEXT_MUT}; font-size: 8pt; font-weight: 700; "
                f"letter-spacing: 1px; background: transparent;"
            )
            c_lay.addWidget(goals_section)
            c_lay.addSpacing(5)

            gc = QWidget()
            gc.setStyleSheet("background: transparent;")
            gc_lay = QVBoxLayout(gc)
            gc_lay.setContentsMargins(0, 0, 0, 0)
            gc_lay.setSpacing(1)

            for ent in day_ents:
                gc_lay.addWidget(_GoalRow(ent, parent_page=self, is_today=is_today))

            # Inline Goal Input (at the bottom of the tasks)
            inline_wrap = QWidget()
            inline_wrap.hide()
            inline_lay = QHBoxLayout(inline_wrap)
            inline_lay.setContentsMargins(0, 3, 0, 3)
            inline_lay.setSpacing(8)

            fake_cb = _CircleCheck(checked=False, is_today=is_today)
            fake_cb.setEnabled(False)
            inline_lay.addWidget(fake_cb, alignment=Qt.AlignmentFlag.AlignVCenter)

            inline_input = QLineEdit()
            inline_input.setPlaceholderText("Enter goal...")
            inline_input.setStyleSheet(
                f"QLineEdit {{ color: {_TEXT_PRI}; font-size: 10pt; "
                f"background: transparent; border: none; letter-spacing: 0.1px; }}"
                f"QLineEdit:focus {{ border: 1px solid {_BORDER_TODAY}; border-radius: 4px; background: #222222; }}"
            )
            # Store the wrapper as a dynamic property on the input so we can easily show it later
            inline_input.setProperty("wrapper", inline_wrap)
            self._inline_inputs[day_idx] = inline_input
            inline_input.returnPressed.connect(
                lambda d=day_idx, inp=inline_input, p=plan.id: self._save_new_goal(d, inp, p)
            )
            inline_lay.addWidget(inline_input, 1)

            gc_lay.addWidget(inline_wrap)

            gc_lay.addStretch(1)
            c_lay.addWidget(gc, 1)
            c_lay.addSpacing(10)

            notes_edit = QTextEdit()
            notes_edit.setFixedHeight(68)
            notes_edit.setPlaceholderText("Add notes…")
            notes_edit.setPlainText(self._day_notes.get(day_idx, ""))
            notes_edit.setStyleSheet(
                f"QTextEdit {{ background: {_NOTE_BG}; color: {_TEXT_SEC}; "
                f"border: 1px solid rgba(255,255,255,0.10); border-radius: 8px; "
                f"padding: 6px 8px; font-size: 9pt; }}"
                f"QTextEdit:focus {{ border: 1px solid rgba(255,255,255,0.18); }}"
            )
            notes_edit.textChanged.connect(
                lambda day=day_idx, te=notes_edit, pid=plan.id: self._save_note(pid, day, te.toPlainText())
            )
            c_lay.addWidget(notes_edit)

            b_lay.addWidget(card)

        b_lay.addStretch(1)
        scroll.setWidget(body)
        self.content_layout.addWidget(scroll, 1)

        self._scroll_area = scroll
        self._scroll_area.horizontalScrollBar().valueChanged.connect(_update_today_highlight)
        QTimer.singleShot(0, _update_today_highlight)

        if saved_scroll is not None:
            QTimer.singleShot(0, lambda: self._scroll_area.horizontalScrollBar().setValue(saved_scroll))
        elif today_index is not None:
            scroll.center_on_day(today_index)

        self.setUpdatesEnabled(True)

    # ── Navigation ─────────────────────────────────────────────────────────────
    def _jump(self, delta: int) -> None:
        self.week_offset += delta
        self._render(reset_scroll=True)

    def _to_today(self) -> None:
        self.week_offset = 0
        self._render(reset_scroll=True)

    # ── Goal actions ───────────────────────────────────────────────────────────
    def _show_inline_input(self, day_idx: int) -> None:
        inp = self._inline_inputs.get(day_idx)
        if inp:
            wrapper = inp.property("wrapper")
            if wrapper:
                wrapper.show()
            inp.show()
            inp.setFocus()

    def _save_new_goal(self, day_idx: int, inp: QLineEdit, plan_id: int) -> None:
        text = inp.text().strip()
        if text:
            entry = WeeklyGoalEntry(title=text, day_of_week=day_idx, planner_id=plan_id)
            self.service.create_weekly_goal_entry(plan_id, entry)
        self.refresh()

    def delete_goal(self, goal_id: int) -> None:
        self.service.delete_weekly_goal_entry(goal_id)
        self._render()

    def toggle_goal_completion(self, goal_id: int, completed: bool) -> None:
        entry = self.service.get_weekly_goal_entry(goal_id)
        if not entry:
            return
        entry.completed = completed
        self.service.update_weekly_goal_entry(goal_id, entry)
        self._render()
