from __future__ import annotations

from datetime import date, datetime

from PySide6.QtGui import QFont, QFontMetrics, QIcon, QPixmap, QPainter, QColor, QPen
from PySide6.QtCore import QDate, QEvent, QSize, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QDialog,
    QDialogButtonBox,
    QScrollArea,
)
from PySide6.QtSvg import QSvgRenderer

from .helper.icons import build_orbit_icon
from .helper.drawer import SlideOutDrawer


class CircleCheck(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QCheckBox { background: transparent; border: none; }")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        # draw circular border
        pen = QPen(QColor('#3a3a3c'))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(r.adjusted(1, 1, -1, -1))

        # draw tick when checked
        if self.isChecked():
            pen = QPen(QColor('#ffffff'))
            pen.setWidth(2)
            painter.setPen(pen)
            w = r.width()
            h = r.height()
            p1 = (int(w * 0.28), int(h * 0.55))
            p2 = (int(w * 0.45), int(h * 0.72))
            p3 = (int(w * 0.75), int(h * 0.32))
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])
            painter.drawLine(p2[0], p2[1], p3[0], p3[1])

        painter.end()


from core.models import Task, TaskStatus
from core.services import ProductivityService
from .helper.toolbar import ToolBar

_TRACKER_BTN_IDLE = """
    QPushButton {
        background: rgba(255,255,255,0.06);
        border: none;
        border-radius: 14px;
        color: #636366;
        font-size: 9px;
        padding: 0px;
    }
    QPushButton:hover {
        background: rgba(255,255,255,0.12);
        color: #e8e8ed;
    }
    QPushButton:pressed {
        background: rgba(255,255,255,0.04);
    }
"""

_TRACKER_BTN_LIVE = """
    QPushButton {
        background: rgba(255,255,255,0.10);
        border: none;
        border-radius: 14px;
        color: #ffffff;
        font-size: 9px;
        padding: 0px;
    }
    QPushButton:hover {
        background: rgba(255,255,255,0.16);
        color: #ffffff;
    }
    QPushButton:pressed {
        background: rgba(255,255,255,0.05);
    }
"""

_ADD_TODAY_BTN = """
    QPushButton {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 8px;
        color: #c8c8cc;
        font-size: 8pt;
        padding: 2px 8px;
        letter-spacing: 0.2px;
    }
    QPushButton:hover {
        background: rgba(255,255,255,0.13);
        border: 1px solid rgba(255,255,255,0.26);
        color: #ffffff;
    }
    QPushButton:pressed {
        background: rgba(255,255,255,0.04);
    }
"""

class _ElidedLabel(QLabel):
    """A label that gracefully elides its text with an ellipsis if it exceeds the width."""
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(1)

    def setText(self, text: str) -> None:
        self._full_text = text
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width())
        
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)
        painter.end()

    def minimumSizeHint(self) -> QSize:
        return QSize(1, super().minimumSizeHint().height())


class TaskItemWidget(QWidget):
    """Monochrome task row widget."""

    def __init__(self, task: Task, parent=None, is_overdue: bool = False):
        super().__init__(parent)
        self.task = task
        self.parent_page = parent
        self.is_tracking = False
        self.is_overdue = is_overdue
        self.session_start_time: datetime | None = None

        self.tracker_timer = QTimer(self)
        self.tracker_timer.setInterval(1000)
        self.tracker_timer.timeout.connect(self._update_tracked_time_label)

        is_completed = task.status == TaskStatus.COMPLETED
        self.is_completed = is_completed

        # ── Outer shell: just horizontal padding, card fills full row width ─────
        container_layout = QHBoxLayout(self)
        container_layout.setContentsMargins(16, 4, 16, 4)

        self.inner_widget = QWidget()
        self.inner_widget.setObjectName("taskCard")
        self.inner_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.inner_widget.setMinimumHeight(64)

        if is_completed:
            border_normal = "rgba(255,255,255,0.04)"
            border_hover  = "rgba(255,255,255,0.07)"
            bg_normal     = "#161618"
            bg_hover      = "#1c1c1e"
        elif is_overdue:
            border_normal = "rgba(255,255,255,0.09)"
            border_hover  = "rgba(255,255,255,0.17)"
            bg_normal     = "#1e1c1c"
            bg_hover      = "#252223"
        else:
            border_normal = "rgba(255,255,255,0.08)"
            border_hover  = "rgba(255,255,255,0.16)"
            bg_normal     = "#1c1c1e"
            bg_hover      = "#242427"

        self.normal_style = f"""
            QWidget#taskCard {{
                background: {bg_normal};
                border-radius: 10px;
                border: 1px solid {border_normal};
            }}
        """
        self.hover_style = f"""
            QWidget#taskCard {{
                background: {bg_hover};
                border-radius: 10px;
                border: 1px solid {border_hover};
            }}
        """

        self.inner_widget.setStyleSheet(self.normal_style)
        self.inner_widget.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.inner_widget.installEventFilter(self)

        # ── Card layout ────────────────────────────────────────────────────
        layout = QHBoxLayout(self.inner_widget)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Left accent strip — slightly warm grey for overdue, no status colour elsewhere
        accent = QWidget()
        accent.setFixedWidth(3)
        if is_completed:
            accent_color = "#2a2a2c"
        elif is_overdue:
            accent_color = "#4a3c3a"   # warm-tinged grey for visual distinction
        else:
            accent_color = "#3a3a3c"
        accent.setStyleSheet(f"QWidget {{ background: {accent_color}; border-radius: 2px; }}")
        layout.addWidget(accent, alignment=Qt.AlignmentFlag.AlignVCenter)

        # ── Circular checkbox ──────────────────────────────────────────────
        self.checkbox = CircleCheck()
        self.checkbox.setChecked(is_completed)
        self.checkbox.clicked.connect(self._toggle_completion)
        layout.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignVCenter)

        # ── Title + progress badge ─────────────────────────────────────────
        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        text_layout.setContentsMargins(6, 0, 0, 0)

        title = _ElidedLabel(task.title)
        if is_completed:
            title.setStyleSheet(
                "color: #484848; text-decoration: line-through; "
                "font-size: 11pt; background: transparent; letter-spacing: 0.1px;"
            )
        elif is_overdue:
            title.setStyleSheet(
                "color: #c8c8cc; font-size: 11pt; font-weight: 500; "
                "background: transparent; letter-spacing: 0.1px;"
            )
        else:
            title.setStyleSheet(
                "color: #e8e8ed; font-size: 11pt; font-weight: 500; "
                "background: transparent; letter-spacing: 0.1px;"
            )
        text_layout.addWidget(title)

        desc_text = task.description if task.description and task.description.strip() else "No description"
        desc_label = _ElidedLabel(desc_text)
        if is_completed:
            desc_label.setStyleSheet("color: #484848; font-size: 8.5pt; background: transparent;")
        else:
            desc_label.setStyleSheet("color: #707075; font-size: 8.5pt; background: transparent;")
        text_layout.addWidget(desc_label)

        # Badge is always created but only shown while tracker is actively running.
        self.progress_badge = QLabel("● Tracking")
        self.progress_badge.setStyleSheet(
            "color: #8e8e93; font-size: 7.5pt; background: transparent; letter-spacing: 0.5px;"
        )
        self.progress_badge.setVisible(False)
        text_layout.addWidget(self.progress_badge)

        layout.addLayout(text_layout, stretch=1)

        # ── Right-side controls ────────────────────────────────────────────
        right_layout = QHBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.tracker_time_label = QLabel(self._format_duration(task.total_tracked_seconds))
        self.tracker_time_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        self.tracker_time_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.tracker_time_label.setStyleSheet(
            "color: #636366; font-size: 8.5pt; background: transparent; "
            "min-width: 52px; letter-spacing: 0.2px;"
        )
        self.tracker_time_label.ensurePolished()
        self.tracker_time_label.setMinimumWidth(max(52, self.tracker_time_label.sizeHint().width()))

        self.tracker_btn = QPushButton("▶")
        self.tracker_btn.setFixedSize(28, 28)
        self.tracker_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tracker_btn.setFont(QFont("Segoe UI Symbol", 10))
        self.tracker_btn.setStyleSheet(_TRACKER_BTN_IDLE)
        self.tracker_btn.clicked.connect(self._toggle_tracker)
        self._set_tracker_button()
        if self.is_completed or self.is_overdue:
            self.tracker_btn.setEnabled(False)
            self.tracker_btn.setCursor(Qt.CursorShape.ArrowCursor)

        right_layout.addWidget(self.tracker_time_label)
        right_layout.addWidget(self.tracker_btn)

        # Date chip — monochrome; overdue/today use brighter grey instead of red
        if task.due_date:
            today_flag   = task.due_date == date.today()
            overdue_flag = task.due_date < date.today()

            if today_flag or overdue_flag:
                chip_color  = "#e8e8ed"
                chip_bg     = "rgba(255,255,255,0.08)"
                chip_border = "rgba(255,255,255,0.20)"
                icon        = "⚑"
                d_str       = "Today" if today_flag else (
                    f"{task.due_date.day} {task.due_date.strftime('%b')}"
                )
            else:
                chip_color  = "#636366"
                chip_bg     = "rgba(255,255,255,0.04)"
                chip_border = "rgba(255,255,255,0.08)"
                icon        = "◷"
                d_str       = f"{task.due_date.day} {task.due_date.strftime('%b')}"

            sep = QWidget()
            sep.setFixedSize(1, 18)
            sep.setStyleSheet("background: rgba(255,255,255,0.08);")
            right_layout.addWidget(sep, alignment=Qt.AlignmentFlag.AlignVCenter)

            self.date_label = QLabel(f"{icon}  {d_str}")
            self.date_label.setStyleSheet(f"""
                color: {chip_color};
                background: {chip_bg};
                border: 1px solid {chip_border};
                font-size: 8.5pt;
                padding: 2px 9px 2px 7px;
                border-radius: 8px;
                letter-spacing: 0.2px;
            """)
            self.date_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.date_label.ensurePolished()
            
            # Fallback to a calculated width if sizeHint fails due to unpolished font/padding
            fm = QFontMetrics(self.date_label.font())
            calc_w = fm.horizontalAdvance(self.date_label.text()) + 24
            
            self.date_label.setMinimumWidth(max(calc_w, self.date_label.sizeHint().width()))
            right_layout.addWidget(self.date_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        else:
            self.date_label = QLabel()

        # ── "Add to Today" button — only rendered for overdue task cards ──
        if is_overdue:
            sep2 = QWidget()
            sep2.setFixedSize(1, 18)
            sep2.setStyleSheet("background: rgba(255,255,255,0.08);")
            right_layout.addWidget(sep2, alignment=Qt.AlignmentFlag.AlignVCenter)

            self.add_today_btn = QPushButton("↺  Add to today")
            self.add_today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.add_today_btn.setStyleSheet(_ADD_TODAY_BTN)
            self.add_today_btn.setFixedHeight(24)
            self.add_today_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.add_today_btn.ensurePolished()
            
            fm = QFontMetrics(self.add_today_btn.font())
            calc_w = fm.horizontalAdvance(self.add_today_btn.text()) + 24
            
            self.add_today_btn.setMinimumWidth(max(calc_w, self.add_today_btn.sizeHint().width()))
            self.add_today_btn.clicked.connect(self._add_to_today)
            right_layout.addWidget(self.add_today_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.flag_label = QLabel()
        self.flag_label.hide()

        layout.addLayout(right_layout)

        container_layout.addWidget(self.inner_widget)
        
        # Lock the entire card's minimum width dynamically based on its calculated contents
        self.inner_widget.ensurePolished()
        self.inner_widget.setMinimumWidth(self.inner_widget.minimumSizeHint().width())

    # ─────────────────────────────────────────────────────────────────────
    #  Event filter
    # ─────────────────────────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if obj is self.inner_widget:
            t = event.type()
            if t == QEvent.Type.Enter:
                self.inner_widget.setStyleSheet(self.hover_style)
            elif t == QEvent.Type.Leave:
                self.inner_widget.setStyleSheet(self.normal_style)
            elif (
                t == QEvent.Type.MouseButtonDblClick
                and event.button() == Qt.MouseButton.LeftButton
            ):
                # allow editing on double-click only for non-completed tasks
                if (not getattr(self, "is_completed", False)) and self.parent_page and hasattr(self.parent_page, "edit_task"):
                    self.parent_page.edit_task(self.task.id)
        return super().eventFilter(obj, event)

    # ─────────────────────────────────────────────────────────────────────
    #  Helpers
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _format_duration(seconds: int) -> str:
        if seconds <= 0:
            return "0s"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    def _update_tracked_time_label(self) -> None:
        total = self.task.total_tracked_seconds
        if self.is_tracking and self.session_start_time:
            total += int((datetime.now() - self.session_start_time).total_seconds())

        if self.is_tracking:
            self.tracker_time_label.setStyleSheet(
                "color: #ffffff; font-size: 8.5pt; background: transparent; "
                "min-width: 52px; letter-spacing: 0.2px;"
            )
            self.tracker_time_label.setText(f"● {self._format_duration(total)}")
        else:
            self.tracker_time_label.setStyleSheet(
                "color: #636366; font-size: 8.5pt; background: transparent; "
                "min-width: 52px; letter-spacing: 0.2px;"
            )
            self.tracker_time_label.setText(self._format_duration(total))

    def _set_tracker_button(self) -> None:
        if self.is_tracking:
            self.tracker_btn.setText("⏸")
            self.tracker_btn.setToolTip("Pause tracker")
            self.tracker_btn.setStyleSheet(_TRACKER_BTN_LIVE)
        else:
            self.tracker_btn.setText("▶")
            self.tracker_btn.setToolTip("Start tracker")
            self.tracker_btn.setStyleSheet(_TRACKER_BTN_IDLE)

    # ─────────────────────────────────────────────────────────────────────
    #  Tracker logic
    # ─────────────────────────────────────────────────────────────────────

    def _toggle_completion(self, checked: bool) -> None:
        if not self.parent_page:
            return
        if self.is_tracking:
            self.pause_tracker()
        if checked:
            self.parent_page.service.tasks.mark_completed(self.task.id)
        else:
            self.task.status = TaskStatus.TODO
            self.parent_page.service.update_task(self.task.id, self.task)
        self.parent_page.refresh()

    def _toggle_tracker(self) -> None:
        # Do not start or toggle tracker for completed or overdue tasks
        if self.task.status == TaskStatus.COMPLETED or self.is_overdue:
            return
        if self.is_tracking:
            self.pause_tracker()
        elif self.parent_page:
            self.parent_page.start_task_tracker(self)
        else:
            self.start_tracker()

    def _add_to_today(self) -> None:
        """Reschedule this overdue task to today and move it back to the active list."""
        if not self.parent_page:
            return
        self.task.due_date = date.today()
        self.parent_page.service.update_task(self.task.id, self.task)
        self.parent_page.refresh()

    def start_tracker(self) -> None:
        # Don't start tracker for completed or overdue tasks
        if self.task.status == TaskStatus.COMPLETED or self.is_overdue:
            return
        if self.is_tracking:
            return
        if self.task.status == TaskStatus.TODO:
            self.task.status = TaskStatus.IN_PROGRESS
            if self.parent_page:
                self.parent_page.service.update_task(self.task.id, self.task)

        self.is_tracking = True
        self.session_start_time = datetime.now()
        self.progress_badge.setVisible(True)
        self._set_tracker_button()
        self._update_tracked_time_label()
        self.tracker_timer.start()

    def pause_tracker(self) -> None:
        if not self.is_tracking:
            return
        elapsed = 0
        if self.session_start_time:
            elapsed = int((datetime.now() - self.session_start_time).total_seconds())

        self.is_tracking = False
        self.session_start_time = None
        self.tracker_timer.stop()
        self.task.total_tracked_seconds += elapsed

        if self.parent_page:
            self.parent_page.service.update_task(self.task.id, self.task)
            if self.task.id in self.parent_page.active_tracker_widgets:
                del self.parent_page.active_tracker_widgets[self.task.id]
            if self.task.id in self.parent_page.active_tracker_start_times:
                del self.parent_page.active_tracker_start_times[self.task.id]

        self.progress_badge.setVisible(False)
        self._set_tracker_button()
        self._update_tracked_time_label()

    def resume_tracker(self, start_time: datetime) -> None:
        self.is_tracking = True
        self.session_start_time = start_time
        self.progress_badge.setVisible(True)
        self._set_tracker_button()
        self._update_tracked_time_label()
        self.tracker_timer.start()


class TaskFormWidget(QWidget):
    saved = Signal(Task)

    def __init__(self, parent=None, task: Task | None = None) -> None:
        super().__init__(parent)
        self.original_task = task
        self._build_ui()
        if task:
            self._load_task(task)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QWidget#FormCard { background: transparent; }")
        form_card = QWidget()
        form_card.setObjectName("FormCard")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(24)

        input_style = """
            QLineEdit, QTextEdit, QDateEdit {
                background-color: #1a1a1c;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 10px;
                color: #ffffff;
                font-size: 10pt;
            }
            QLineEdit:focus, QTextEdit:focus, QDateEdit:focus {
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """

        label_style = "color: #e8e8ed; font-size: 9.5pt; font-weight: 500;"

        # ── Title ──
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)
        lbl_title = QLabel("Title")
        lbl_title.setStyleSheet(label_style)
        self.title = QLineEdit()
        self.title.setPlaceholderText("Enter task title")
        self.title.setStyleSheet(input_style)
        title_layout.addWidget(lbl_title)
        title_layout.addWidget(self.title)

        # ── Description ──
        desc_container = QWidget()
        desc_layout = QVBoxLayout(desc_container)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        desc_layout.setSpacing(8)
        lbl_desc = QLabel("Description")
        lbl_desc.setStyleSheet(label_style)
        self.description = QTextEdit()
        self.description.setPlaceholderText("Enter task description")
        self.description.setMaximumHeight(120)
        self.description.setStyleSheet(input_style)
        desc_layout.addWidget(lbl_desc)
        desc_layout.addWidget(self.description)

        # ── Due Date ──
        due_container = QWidget()
        due_layout = QVBoxLayout(due_container)
        due_layout.setContentsMargins(0, 0, 0, 0)
        due_layout.setSpacing(8)
        self.due_enabled = QCheckBox("Has due date")
        self.due_enabled.setStyleSheet("color: #e8e8ed; font-size: 9.5pt;")
        self.due_date = QDateEdit(QDate.currentDate())
        self.due_date.setCalendarPopup(True)
        self.due_date.setStyleSheet(input_style + " QDateEdit::drop-down { border: none; width: 30px; }")
        due_layout.addWidget(self.due_enabled)
        due_layout.addWidget(self.due_date)

        form_layout.addWidget(title_container)
        form_layout.addWidget(desc_container)
        form_layout.addWidget(due_container)
        form_layout.addStretch(1)

        scroll.setWidget(form_card)
        layout.addWidget(scroll)

        # ── Action Button ──
        btn_text = "Save Task" if self.original_task else "Create Task"
        self.save_btn = QPushButton(btn_text)
        self.save_btn.setFixedHeight(44)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2c;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: 500;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #353538;
            }
        """)
        self.save_btn.clicked.connect(lambda: self.saved.emit(self.get_task_data()))
        self.title.returnPressed.connect(self.save_btn.click)
        layout.addWidget(self.save_btn)

    def _load_task(self, task: Task) -> None:
        self.title.setText(task.title)
        self.description.setPlainText(task.description)
        self.due_enabled.setChecked(task.due_date is not None)
        if task.due_date:
            self.due_date.setDate(QDate(task.due_date.year, task.due_date.month, task.due_date.day))

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
        painter.end()
        return QIcon(pix)

    def _read_date(self, widget: QDateEdit, enabled: QCheckBox) -> date | None:
        return widget.date().toPython() if enabled.isChecked() else None

    def get_task_data(self) -> Task:
        return Task(
            title=self.title.text().strip() or "Untitled task",
            description=self.description.toPlainText().strip(),
            due_date=self._read_date(self.due_date, self.due_enabled),
            status=self.original_task.status if self.original_task else TaskStatus.TODO,
            total_tracked_seconds=self.original_task.total_tracked_seconds if self.original_task else 0,
            id=self.original_task.id if self.original_task else None
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Shared list-widget stylesheet (used by all three section widgets)
# ─────────────────────────────────────────────────────────────────────────────

_LIST_WIDGET_STYLE = """
    QListWidget {
        background: transparent;
        border: none;
        outline: 0;
    }
    QListWidget::item {
        background: transparent;
        border: none;
    }
    QListWidget::item:selected {
        background: transparent;
    }
    QListWidget::item:hover {
        background: transparent;
    }
"""


class OverdueTasksSection:
    """Collapsible section that surfaces tasks whose deadline has passed."""

    def __init__(self, parent_page=None):
        self.collapsed = False
        self.parent_page = parent_page

        self.header_widget = QWidget()
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(15, 10, 15, 10)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setFixedSize(20, 20)
        self.collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #c8c8cc;
                font-size: 12px;
                padding: 0px;
            }
            QPushButton:hover { color: #ffffff; }
        """)
        self.collapse_btn.setText("▼")
        self.collapse_btn.clicked.connect(self._toggle_collapse)

        header_layout.addStretch()
        header_layout.addWidget(self.collapse_btn)

        self.header_label = QLabel("Overdue")
        self.header_label.setStyleSheet(
            "font-weight: bold; font-size: 11pt; color: #c8c8cc; margin-left: 6px;"
        )
        header_layout.addWidget(self.header_label)

        self.count_label = QLabel("(0)")
        self.count_label.setStyleSheet(
            "color: rgba(255,255,255,0.4); font-size: 10pt; margin-left: 5px;"
        )
        header_layout.addWidget(self.count_label)

        header_layout.addStretch()

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(_LIST_WIDGET_STYLE)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def add_to_layout(self, layout):
        layout.addWidget(self.header_widget)
        layout.addWidget(self.list_widget, stretch=1)

    def hide(self):
        self.header_widget.hide()
        self.list_widget.hide()

    def show(self):
        self.header_widget.show()
        if not self.collapsed:
            self.list_widget.show()

    # ── Collapse / expand ──────────────────────────────────────────────────

    def _toggle_collapse(self):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.collapse_btn.setText("▶")
            self.list_widget.hide()
        else:
            self.collapse_btn.setText("▼")
            self.list_widget.show()

    # ── Populate ───────────────────────────────────────────────────────────

    def populate(self, overdue_tasks: list[Task]) -> None:
        self.list_widget.clear()
        self.count_label.setText(f"({len(overdue_tasks)})")
        total_height = 0
        for task in overdue_tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            widget = TaskItemWidget(task, parent=self.parent_page, is_overdue=True)
            item_height = widget.sizeHint().height()
            item.setSizeHint(QSize(0, item_height))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            total_height += item_height


class CompletedTasksSection:
    def __init__(self, parent_page=None):
        self.collapsed = False
        self.parent_page = parent_page

        self.header_widget = QWidget()
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(15, 10, 15, 10)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setFixedSize(20, 20)
        self.collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: white;
                font-size: 12px;
                padding: 0px;
            }
            QPushButton:hover { color: #ffffff; }
        """)
        self.collapse_btn.setText("▼")
        self.collapse_btn.clicked.connect(self._toggle_collapse)

        header_layout.addStretch()
        header_layout.addWidget(self.collapse_btn)

        self.header_label = QLabel("Completed Tasks")
        self.header_label.setStyleSheet(
            "font-weight: bold; font-size: 11pt; color: rgba(255,255,255,0.9); margin-left: 6px;"
        )
        header_layout.addWidget(self.header_label)

        self.count_label = QLabel("(0)")
        self.count_label.setStyleSheet(
            "color: rgba(255,255,255,0.6); font-size: 10pt; margin-left: 5px;"
        )
        header_layout.addWidget(self.count_label)

        header_layout.addStretch()

        # ── Task list ──────────────────────────────────────────────────────
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(_LIST_WIDGET_STYLE)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # ── Archive button ─────────────────────────────────────────────────
        self.archive_btn = QPushButton("✓ Move completed tasks to archive")
        self.archive_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # shrink to content so hover background only covers the text area
        self.archive_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.archive_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #c8c8cc;
                padding: 8px 12px;
                margin: 10px 15px 15px 15px;
                border-radius: 8px;
            }
            QPushButton:hover {
                color: #e8e8ed;
                background: rgba(255,255,255,0.03);
            }
            QPushButton:pressed {
                background: rgba(255,255,255,0.06);
            }
        """)
        self.archive_btn.clicked.connect(self._archive_completed)

    def add_to_layout(self, layout):
        # Divider is now re-added directly above header to match previous behavior
        top_divider = QWidget()
        top_divider.setFixedHeight(1)
        top_divider.setStyleSheet("background: rgba(255,255,255,0.07);")
        self.top_divider = top_divider
        
        layout.addWidget(self.top_divider)
        layout.addWidget(self.header_widget)
        layout.addWidget(self.list_widget, stretch=1)
        layout.addWidget(self.archive_btn, 0, Qt.AlignmentFlag.AlignHCenter)

    def hide(self):
        if hasattr(self, 'top_divider'):
            self.top_divider.hide()
        self.header_widget.hide()
        self.list_widget.hide()
        self.archive_btn.hide()

    def show(self):
        if hasattr(self, 'top_divider'):
            self.top_divider.show()
        self.header_widget.show()
        if not self.collapsed:
            self.list_widget.show()
            self.archive_btn.show()

    def _toggle_collapse(self):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.collapse_btn.setText("▶")
            self.list_widget.hide()
            self.archive_btn.hide()
        else:
            self.collapse_btn.setText("▼")
            self.list_widget.show()
            self.archive_btn.show()

    def _archive_completed(self):
        if self.parent_page:
            self.parent_page.archive_completed_tasks()

    def populate(self, completed_tasks: list[Task]) -> None:
        self.list_widget.clear()
        self.count_label.setText(f"({len(completed_tasks)})")
        total_height = 0
        for task in completed_tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            widget = TaskItemWidget(task, parent=self.parent_page)
            item_height = widget.sizeHint().height()
            item.setSizeHint(QSize(0, item_height))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            total_height += item_height


class TasksPage(QWidget):
    def __init__(self, service: ProductivityService) -> None:
        super().__init__()
        self.service = service
        self._selected_task_id: int | None = None
        # support multiple concurrent trackers: map task_id -> widget and start time
        self.active_tracker_widgets: dict[int, TaskItemWidget] = {}
        self.active_tracker_start_times: dict[int, datetime] = {}
        self.drawer = SlideOutDrawer(width=380, parent=self)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar is now inside body_widget so it slides with the content

        # Horizontal layout for body + drawer
        h_body_container = QWidget()
        h_body_layout = QHBoxLayout(h_body_container)
        h_body_layout.setContentsMargins(0, 0, 0, 0)
        h_body_layout.setSpacing(0)

        # Body container
        body_widget = QWidget()
        layout = QVBoxLayout(body_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        self.toolbar = ToolBar()
        layout.addWidget(self.toolbar)

        # Centered container capped at 960 px — constrains ALL list widgets uniformly
        content_container = QWidget()
        content_container.setMaximumWidth(960)
        content_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # ── Active task list ───────────────────────────────────────────────
        self.empty_label = QLabel("No tasks available")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11pt;")
        content_layout.addWidget(self.empty_label, stretch=1)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(_LIST_WIDGET_STYLE)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_layout.addWidget(self.list_widget, stretch=1)

        # ── Overdue tasks section (hidden until there are overdue tasks) ───
        self.overdue_section = OverdueTasksSection(parent_page=self)
        self.overdue_section.add_to_layout(content_layout)
        self.overdue_section.hide()

        # ── Completed tasks section ────────────────────────────────────────
        self.completed_section = CompletedTasksSection(parent_page=self)
        self.completed_section.add_to_layout(content_layout)
        self.completed_section.hide()

        # Center the container horizontally
        center_layout = QHBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addStretch(1)
        center_layout.addWidget(content_container, stretch=4)
        center_layout.addStretch(1)
        layout.addLayout(center_layout, stretch=1)
        
        h_body_layout.addWidget(body_widget, stretch=1)
        h_body_layout.addWidget(self.drawer)
        
        main_layout.addWidget(h_body_container, stretch=1)

        # Connections
        self.toolbar.add_button.clicked.connect(self.add_task)

    # ─────────────────────────────────────────────────────────────────────
    #  Tracker management
    # ─────────────────────────────────────────────────────────────────────

    def start_task_tracker(self, widget: TaskItemWidget) -> None:
        task_id = widget.task.id
        if task_id in self.active_tracker_widgets:
            return

        widget.start_tracker()
        self.active_tracker_widgets[task_id] = widget
        self.active_tracker_start_times[task_id] = widget.session_start_time

    def clear_active_tracker(self) -> None:
        self.active_tracker_widgets.clear()
        self.active_tracker_start_times.clear()

    # ─────────────────────────────────────────────────────────────────────
    #  Refresh
    # ─────────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        tasks = self.service.tasks.list()
        today = date.today()

        # ── Categorise tasks into three buckets ───────────────────────────
        # overdue: not completed, has a past due date
        # active:  not completed, no due date OR due date is today or future
        # completed: status == COMPLETED (regardless of date)
        active_tasks = [
            t for t in tasks
            if t.status != TaskStatus.COMPLETED
            and (t.due_date is None or t.due_date >= today)
        ]
        overdue_tasks = [
            t for t in tasks
            if t.status != TaskStatus.COMPLETED
            and t.due_date is not None
            and t.due_date < today
        ]
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]

        # Preserve running tracker state across the refresh
        active_task_ids = set(self.active_tracker_widgets.keys())

        # ── Populate active tasks ──────────────────────────────────────────
        self.list_widget.clear()
        total_active_height = 0
        for task in active_tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            widget = TaskItemWidget(task, parent=self)
            if task.id in active_task_ids and self.active_tracker_start_times.get(task.id) is not None:
                widget.resume_tracker(self.active_tracker_start_times[task.id])
            item_height = widget.sizeHint().height()
            item.setSizeHint(QSize(0, item_height))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            total_active_height += item_height
        
        if active_tasks:
            self.empty_label.hide()
            self.list_widget.show()
            if self.list_widget.currentRow() < 0:
                self.list_widget.setCurrentRow(0)
        else:
            self.empty_label.show()
            self.list_widget.hide()

        # ── Populate / hide overdue section ───────────────────────────────
        if overdue_tasks:
            self.overdue_section.show()
            self.overdue_section.populate(overdue_tasks)
        else:
            self.overdue_section.hide()

        # ── Populate / hide completed section ─────────────────────────────
        if completed_tasks:
            self.completed_section.show()
            self.completed_section.populate(completed_tasks)
        else:
            self.completed_section.hide()

    # ─────────────────────────────────────────────────────────────────────
    #  Task CRUD helpers
    # ─────────────────────────────────────────────────────────────────────

    def _selected_task_id_value(self) -> int | None:
        item = self.list_widget.currentItem()
        if item is None:
            return self._selected_task_id
        value = item.data(Qt.ItemDataRole.UserRole)
        return int(value) if value is not None else None

    def add_task(self) -> None:
        form = TaskFormWidget(self)
        form.saved.connect(self._on_task_saved)
        self.drawer.set_title("Create Task")
        self.drawer.set_content(form)
        self.drawer.open_drawer()

    def edit_task(self, task_id: int | None = None) -> None:
        if task_id is None:
            task_id = self._selected_task_id_value()
        if task_id is None:
            return
        task = self.service.tasks.get(task_id)
        if not task:
            return
        form = TaskFormWidget(self, task)
        form.saved.connect(self._on_task_saved)
        self.drawer.set_title("Edit Task")
        self.drawer.set_content(form)
        self.drawer.open_drawer()

    def _on_task_saved(self, task: Task) -> None:
        self.drawer.close_drawer()
        if task.id is None:
            task_id = self.service.create_task(task)
        else:
            task_id = task.id
            self.service.update_task(task_id, task)
        self._selected_task_id = task_id
        self.refresh()
        self.select_task(task_id)

    def delete_task(self) -> None:
        task_id = self._selected_task_id_value()
        if task_id is None:
            return
        self.service.delete_task(task_id)
        self._selected_task_id = None
        self.refresh()

    def select_task(self, task_id: int) -> None:
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if int(item.data(Qt.ItemDataRole.UserRole)) == task_id:
                self.list_widget.setCurrentRow(row)
                break

    def mark_selected_completed(self) -> None:
        task_id = self._selected_task_id_value()
        if task_id is None:
            return
        self.service.tasks.mark_completed(task_id)
        self.refresh()
        self.select_task(task_id)

    def mark_selected_skipped(self) -> None:
        task_id = self._selected_task_id_value()
        if task_id is None:
            return
        self.service.tasks.mark_skipped(task_id)
        self.refresh()
        self.select_task(task_id)

    def carry_forward(self) -> None:
        self.service.tasks.carry_forward()
        self.refresh()

    def archive_completed_tasks(self) -> None:
        tasks = self.service.tasks.list()
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        for task in completed_tasks:
            self.service.delete_task(task.id)
        self.refresh()
