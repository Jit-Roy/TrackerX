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

from ..core.models import WeeklyGoalEntry, WeeklyPlan
from ..core.services import ProductivityService
from .icons import build_orbit_icon


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

        if self._checked:
            # Filled grey circle
            p.setBrush(QBrush(accent))
            p.setPen(QPen(accent, 1.5))
            p.drawEllipse(rect)

            # Dark tick mark  (✓ drawn as two line segments)
            tick_pen = QPen(
                QColor("#111111"), 1.8,
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

        else:
            # Border-only circle
            ring_color = accent if self._is_today else QColor("#444444")
            if self._hovered:
                ring_color = accent

            p.setBrush(
                QBrush(QColor(200, 200, 200, 40)) if self._hovered
                else Qt.BrushStyle.NoBrush
            )
            p.setPen(QPen(ring_color, 1.5))
            p.drawEllipse(rect)

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

        self.lbl = QLabel(self.entry.title or "New goal")
        self.lbl.setWordWrap(True)
        self.lbl.setStyleSheet(
            f"color: {(_TEXT_MUT if done else _TEXT_PRI)}; font-size: 10pt; "
            f"background: transparent; letter-spacing: 0.1px;"
            + ("; text-decoration: line-through;" if done else "")
        )
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
        if self.entry.id and self.parent_page:
            self.parent_page.edit_goal(self.entry.id)

    def _delete(self) -> None:
        if self.entry.id and self.parent_page:
            self.parent_page.delete_goal(self.entry.id)


# ── Goal form dialog ───────────────────────────────────────────────────────────
class GoalFormDialog(QDialog):
    def __init__(
        self,
        parent=None,
        entry: WeeklyGoalEntry | None = None,
        day_label: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowIcon(build_orbit_icon(16))
        self.setWindowTitle("Edit Goal" if entry else "Add Goal")
        self.setModal(True)
        self.resize(400, 160)
        self.entry = entry
        self.day_label = day_label
        self._build()
        if entry:
            self.title_edit.setText(entry.title)
        self.setStyleSheet(f"""
            QDialog   {{ background: #1a1a1a; color: {_TEXT_PRI}; }}
            QLabel    {{ color: {_TEXT_SEC}; font-size: 9pt; background: transparent; }}
            QLineEdit {{
                background: #222222;
                color: {_TEXT_PRI};
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 9.5pt;
            }}
            QLineEdit:focus {{
                border: 1px solid rgba(255,255,255,0.30);
            }}
        """)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 16)
        lay.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("What do you want to accomplish?")
        form.addRow(QLabel("Goal"), self.title_edit)
        form.addRow(QLabel("Day"),  QLabel(self.day_label))
        lay.addLayout(form)

        row = QHBoxLayout()
        row.addStretch()
        save = QPushButton("Save")
        save.setFixedHeight(30)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.setStyleSheet(
            f"QPushButton {{ background: {_ACCENT}; color: #111111; border: none; "
            f"border-radius: 8px; padding: 0 18px; font-weight: 700; font-size: 9pt; }}"
            f"QPushButton:hover {{ background: {_ACCENT_HOVER}; }}"
        )
        save.clicked.connect(self.accept)
        row.addWidget(save)
        lay.addLayout(row)

    def get_goal_data(self) -> WeeklyGoalEntry:
        return WeeklyGoalEntry(
            title=self.title_edit.text().strip() or "Untitled goal",
            day_of_week=self.entry.day_of_week if self.entry else 0,
            completed=self.entry.completed if self.entry else False,
            planner_id=self.entry.planner_id if self.entry else None,
            id=self.entry.id if self.entry else None,
        )


# ── Planner page ───────────────────────────────────────────────────────────────
class PlannerPage(QWidget):
    def __init__(self, service: ProductivityService) -> None:
        super().__init__()
        self.service = service
        self.week_offset = 0
        self._day_notes: dict[int, str] = {}
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

    # ── Public ─────────────────────────────────────────────────────────────────
    def refresh(self) -> None:
        self._render()

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
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ color: {_TEXT_SEC}; background: transparent; "
            f"border: none; font-size: 16pt; padding: 0; }}"
            f"QPushButton:hover {{ color: {_TEXT_PRI}; }}"
        )
        btn.clicked.connect(callback)
        return btn

    def _save_note(self, plan_id: int, day_of_week: int, text: str) -> None:
        self._day_notes[day_of_week] = text
        self.service.save_weekly_plan_note(plan_id, day_of_week, text)

    # ── Render ─────────────────────────────────────────────────────────────────
    def _render(self) -> None:
        self.setUpdatesEnabled(False)
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if w := item.widget():
                w.deleteLater()

        today     = date.today()
        days      = self._week_days()
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
        today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        today_btn.setStyleSheet(
            f"QPushButton {{ color: {_TEXT_SEC}; background: transparent; border: none; font-size: 9.5pt; }}"
            f"QPushButton:hover {{ color: {_TEXT_PRI}; }}"
        )
        today_btn.clicked.connect(self._to_today)
        n_lay.addWidget(today_btn)
        n_lay.addStretch(1)
        self.content_layout.addWidget(nav)

        # ── Day cards ─────────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
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
            plus_btn.clicked.connect(lambda d=day_idx: self.add_goal_for_day(d))
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

        today_index = next(
            (idx for idx, (_, _, d) in enumerate(days) if d == today),
            None,
        )
        if today_index is not None:
            self._center_today_card(scroll, today_index)

        self.setUpdatesEnabled(True)

    # ── Navigation ─────────────────────────────────────────────────────────────
    def _center_today_card(self, scroll: QScrollArea, day_index: int) -> None:
        def center() -> None:
            bar = scroll.horizontalScrollBar()
            viewport_width = scroll.viewport().width()
            card_width = _DAY_WIDTH
            card_spacing = 10
            left_margin = 28
            x_center = left_margin + day_index * (card_width + card_spacing) + card_width / 2
            target = int(x_center - viewport_width / 2)
            bar.setValue(max(0, min(target, bar.maximum())))

        QTimer.singleShot(0, center)

    def _jump(self, delta: int) -> None:
        self.week_offset += delta
        self._render()

    def _to_today(self) -> None:
        self.week_offset = 0
        self._render()

    # ── Goal actions ───────────────────────────────────────────────────────────
    def add_goal_for_today(self) -> None:
        self.add_goal_for_day(date.today().weekday())

    def add_goal_for_day(self, day_of_week: int) -> None:
        plan     = self.service.get_or_create_weekly_plan(self._week_days()[0][2])
        day_name = self._week_days()[day_of_week][0]
        dialog   = GoalFormDialog(self, None, day_label=day_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            entry = dialog.get_goal_data()
            entry.day_of_week = day_of_week
            entry.planner_id  = plan.id
            self.service.create_weekly_goal_entry(plan.id, entry)
            self._render()

    def edit_goal(self, goal_id: int) -> None:
        entry = self.service.get_weekly_goal_entry(goal_id)
        if not entry:
            return
        dialog = GoalFormDialog(
            self, entry,
            day_label=self._week_days()[entry.day_of_week][0],
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.service.update_weekly_goal_entry(goal_id, dialog.get_goal_data())
            self._render()

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