from __future__ import annotations

from datetime import date, datetime

from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPen
from PySide6.QtCore import QDate, QEvent, QTimer, QSize, Qt
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
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QDialog,
    QDialogButtonBox,
    QScrollArea,
)
from PySide6.QtSvg import QSvgRenderer


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
            # coordinates relative to widget size
            w = r.width()
            h = r.height()
            # simple tick: start lower-left, middle, upper-right
            p1 = (int(w * 0.28), int(h * 0.55))
            p2 = (int(w * 0.45), int(h * 0.72))
            p3 = (int(w * 0.75), int(h * 0.32))
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])
            painter.drawLine(p2[0], p2[1], p3[0], p3[1])

        painter.end()

from ..core.models import Task, TaskStatus
from ..core.services import ProductivityService
from .toolbar import ToolBar

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


class TaskItemWidget(QWidget):
    """Monochrome task row widget."""

    def __init__(self, task: Task, parent=None):
        super().__init__(parent)
        self.task = task
        self.parent_page = parent
        self.is_tracking = False
        self.session_start_time: datetime | None = None

        self.tracker_timer = QTimer(self)
        self.tracker_timer.setInterval(1000)
        self.tracker_timer.timeout.connect(self._update_tracked_time_label)

        is_completed = task.status == TaskStatus.COMPLETED
        self.is_completed = is_completed

        # ── Outer centering shell ──────────────────────────────────────────
        container_layout = QHBoxLayout(self)
        container_layout.setContentsMargins(0, 4, 0, 4)

        self.inner_widget = QWidget()
        self.inner_widget.setObjectName("taskCard")
        self.inner_widget.setFixedWidth(820)

        if is_completed:
            border_normal = "rgba(255,255,255,0.04)"
            border_hover  = "rgba(255,255,255,0.07)"
            bg_normal     = "#161618"
            bg_hover      = "#1c1c1e"
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

        # Left accent strip — uniform grey, no status colour
        accent = QWidget()
        accent.setFixedWidth(3)
        accent.setStyleSheet(
            f"QWidget {{ background: {'#2a2a2c' if is_completed else '#3a3a3c'}; border-radius: 2px; }}"
        )
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

        title = QLabel(task.title)
        if is_completed:
            title.setStyleSheet(
                "color: #484848; text-decoration: line-through; "
                "font-size: 11pt; background: transparent; letter-spacing: 0.1px;"
            )
        else:
            title.setStyleSheet(
                "color: #e8e8ed; font-size: 11pt; font-weight: 500; "
                "background: transparent; letter-spacing: 0.1px;"
            )
        text_layout.addWidget(title)

        # Badge is always created but only shown while tracker is actively running.
        # start_tracker / resume_tracker show it; pause_tracker hides it.
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
        self.tracker_time_label.setStyleSheet(
            "color: #636366; font-size: 8.5pt; background: transparent; "
            "min-width: 52px; letter-spacing: 0.2px;"
        )

        self.tracker_btn = QPushButton("▶")
        self.tracker_btn.setFixedSize(28, 28)
        self.tracker_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Use a symbol font that renders the pause glyph in monochrome
        # (prevents platform color emoji rendering which can appear blue)
        self.tracker_btn.setFont(QFont("Segoe UI Symbol", 10))
        self.tracker_btn.setStyleSheet(_TRACKER_BTN_IDLE)
        self.tracker_btn.clicked.connect(self._toggle_tracker)
        self._set_tracker_button()
        if self.is_completed:
            # completed tasks should not be trackable
            self.tracker_btn.setEnabled(False)
            self.tracker_btn.setCursor(Qt.CursorShape.ArrowCursor)

        right_layout.addWidget(self.tracker_time_label)
        right_layout.addWidget(self.tracker_btn)

        # Date chip — monochrome; overdue/today use brighter grey instead of red
        if task.due_date:
            today_flag = task.due_date == date.today()
            overdue    = task.due_date < date.today()

            if today_flag or overdue:
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
            right_layout.addWidget(self.date_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        else:
            self.date_label = QLabel()

        self.flag_label = QLabel()
        self.flag_label.hide()

        layout.addLayout(right_layout)

        container_layout.addStretch(1)
        container_layout.addWidget(self.inner_widget)
        container_layout.addStretch(1)

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
        # Do not start or toggle tracker for completed tasks
        if self.task.status == TaskStatus.COMPLETED:
            return
        if self.is_tracking:
            self.pause_tracker()
        elif self.parent_page:
            self.parent_page.start_task_tracker(self)
        else:
            self.start_tracker()

    def start_tracker(self) -> None:
        # Don't start tracker for completed tasks
        if self.task.status == TaskStatus.COMPLETED:
            return
        if self.is_tracking:
            return
        if self.task.status == TaskStatus.TODO:
            self.task.status = TaskStatus.IN_PROGRESS
            if self.parent_page:
                self.parent_page.service.update_task(self.task.id, self.task)

        self.is_tracking = True
        self.session_start_time = datetime.now()
        self.progress_badge.setVisible(True)   # ← show only when live
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
            if self.parent_page.active_tracker_widget is self:
                self.parent_page.clear_active_tracker()

        self.progress_badge.setVisible(False)  # ← hide when paused
        self._set_tracker_button()
        self._update_tracked_time_label()

    def resume_tracker(self, start_time: datetime) -> None:
        self.is_tracking = True
        self.session_start_time = start_time
        self.progress_badge.setVisible(True)   # ← restore on resume
        self._set_tracker_button()
        self._update_tracked_time_label()
        self.tracker_timer.start()


class TaskFormDialog(QDialog):
    def __init__(self, parent=None, task: Task | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Task Details" if task else "Create Task")
        self.resize(500, 300)
        self.original_task = task
        self._build_ui()
        if task:
            self._load_task(task)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_card = QWidget()
        form = QFormLayout(form_card)

        self.title = QLineEdit()
        self.description = QTextEdit()
        self.description.setMaximumHeight(80)
        self.due_enabled = QCheckBox("Has due date")
        self.due_date = QDateEdit(QDate.currentDate())
        self.due_date.setCalendarPopup(True)

        form.addRow("Title", self.title)
        form.addRow("Description", self.description)
        form.addRow(self.due_enabled, self.due_date)
        
        scroll.setWidget(form_card)
        layout.addWidget(scroll)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_task(self, task: Task) -> None:
        self.title.setText(task.title)
        self.description.setPlainText(task.description)
        self.due_enabled.setChecked(task.due_date is not None)
        if task.due_date:
            self.due_date.setDate(QDate(task.due_date.year, task.due_date.month, task.due_date.day))

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


class CompletedTasksSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.collapsed = False
        self.parent_page = parent
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(0)
        
        # Header with collapse/expand button and count
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        self.collapse_btn = QPushButton()
        self.collapse_btn.setFixedSize(20, 20)
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: white;
                font-size: 14px;
                padding: 0px;
            }
        """)
        self.collapse_btn.setText("▼")
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        
        header_layout.addStretch()
        header_layout.addWidget(self.collapse_btn)
        
        self.header_label = QLabel("Completed Tasks")
        self.header_label.setStyleSheet("font-weight: bold; font-size: 11pt; color: rgba(255, 255, 255, 0.9);")
        header_layout.addWidget(self.header_label)
        
        self.count_label = QLabel("(0)")
        self.count_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); margin-left: 5px;")
        header_layout.addWidget(self.count_label)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # List widget for completed tasks
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
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
        """)
        layout.addWidget(self.list_widget, 1)
        
        # Archive button
        self.archive_btn = QPushButton("✓ Move completed tasks to archive")
        self.archive_btn.setStyleSheet("""
            QPushButton {
                    background: transparent;
                    border: none;
                color: white;
                padding: 8px 12px;
                margin: 10px 15px 15px 15px;
            }
        """)
        self.archive_btn.clicked.connect(self._archive_completed)
        layout.addWidget(self.archive_btn)
    
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
    
    def populate(self, completed_tasks):
        self.list_widget.clear()
        self.count_label.setText(f"({len(completed_tasks)})")
        for task in completed_tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            widget = TaskItemWidget(task, parent=self.parent_page)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)


class TasksPage(QWidget):
    def __init__(self, service: ProductivityService) -> None:
        super().__init__()
        self.service = service
        self._selected_task_id: int | None = None
        self.active_tracker_widget: TaskItemWidget | None = None
        self.active_tracker_task_id: int | None = None
        self.active_tracker_start_time: datetime | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Toolbar
        self.toolbar = ToolBar()
        layout.addWidget(self.toolbar)

        # Scroll area for task content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Active task list
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
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
        """)
        content_layout.addWidget(self.list_widget, 1)

        # Completed tasks section
        self.completed_section = CompletedTasksSection(parent=self)
        self.completed_section.hide()
        content_layout.addWidget(self.completed_section)
        
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)

        # Connections
        self.toolbar.add_button.clicked.connect(self.add_task)

    def start_task_tracker(self, widget: TaskItemWidget) -> None:
        if self.active_tracker_widget is widget:
            return
        if self.active_tracker_widget is not None:
            self.active_tracker_widget.pause_tracker()

        self.active_tracker_widget = widget
        widget.start_tracker()
        self.active_tracker_task_id = widget.task.id
        self.active_tracker_start_time = widget.session_start_time

    def clear_active_tracker(self) -> None:
        self.active_tracker_widget = None
        self.active_tracker_task_id = None
        self.active_tracker_start_time = None


    def refresh(self) -> None:
        tasks = self.service.tasks.list()
        
        # Separate active and completed tasks
        active_tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED]
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        
        # Preserve active tracker state while refreshing
        active_task_id = self.active_tracker_task_id
        active_start = self.active_tracker_start_time
        self.active_tracker_widget = None

        # Populate active tasks
        self.list_widget.clear()
        for task in active_tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            widget = TaskItemWidget(task, parent=self)
            if active_task_id == task.id and active_start is not None:
                self.active_tracker_widget = widget
                widget.resume_tracker(active_start)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
        if active_tasks and self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)
        
        # Show/hide and populate completed tasks section
        if completed_tasks:
            self.completed_section.show()
            self.completed_section.populate(completed_tasks)
        else:
            self.completed_section.hide()

    def _selected_task_id_value(self) -> int | None:
        item = self.list_widget.currentItem()
        if item is None:
            return self._selected_task_id
        value = item.data(Qt.ItemDataRole.UserRole)
        return int(value) if value is not None else None

    def add_task(self) -> None:
        dialog = TaskFormDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            task = dialog.get_task_data()
            task_id = self.service.create_task(task)
            self._selected_task_id = task_id
            self.refresh()
            self.select_task(task_id)

    def edit_task(self, task_id: int | None = None) -> None:
        if task_id is None:
            task_id = self._selected_task_id_value()
        if task_id is None:
            return
        task = self.service.tasks.get(task_id)
        if not task:
            return
        dialog = TaskFormDialog(self, task)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_task = dialog.get_task_data()
            self.service.update_task(task_id, updated_task)
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