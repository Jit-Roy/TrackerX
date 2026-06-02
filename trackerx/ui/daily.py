from __future__ import annotations

from datetime import date

from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtCore import QDate, QEvent, QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
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
from PySide6.QtGui import QPainter, QPixmap, QIcon

from ..core.models import Task, TaskStatus
from ..core.services import ProductivityService
from .toolbar import ToolBar

class TaskItemWidget(QWidget):
    def __init__(self, task: Task, parent=None):
        super().__init__(parent)
        self.task = task
        self.parent_page = parent
        
        # Center the widget horizontally and set max width
        container_layout = QHBoxLayout(self)
        container_layout.setContentsMargins(0, 5, 0, 5)
        
        # Inner wrapper that actually draws the "box"
        self.inner_widget = QWidget()
        self.inner_widget.setFixedWidth(800)

        self.normal_style = (
            """
            QWidget {
                background: #1f1f1f;
                border-radius: 8px;
            }
            """
            if task.status != TaskStatus.COMPLETED
            else
            """
            QWidget {
                background: #161616;
                border-radius: 8px;
            }
            """
        )

        self.hover_style = """
            QWidget {
                background: #2a2a2a;
                border-radius: 8px;
            }
        """

        self.inner_widget.setStyleSheet(self.normal_style)

        self.inner_widget.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.inner_widget.installEventFilter(self)
        
        layout = QHBoxLayout(self.inner_widget)
        layout.setContentsMargins(15, 10, 15, 10)
        
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(task.status == TaskStatus.COMPLETED)
        self.checkbox.setStyleSheet("QCheckBox::indicator { width: 18px; height: 18px; }")
        self.checkbox.clicked.connect(self._toggle_completion)
        layout.addWidget(self.checkbox)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(4)
        
        title = QLabel(task.title)
        if task.status == TaskStatus.COMPLETED:
            title.setStyleSheet("text-decoration: line-through; color: #555555; font-size: 11pt; background: transparent;")
        else:
            title.setStyleSheet("font-size: 11pt; background: transparent;")
            
        main_layout.addWidget(title)
        
        layout.addLayout(main_layout)
        layout.addStretch()
        
        right_layout = QVBoxLayout()
        flag_label = QLabel("⚑")
        flag_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(flag_label)
        
        if task.due_date:
            from datetime import date
            if task.due_date == date.today():
                date_str = "Today"
                color = "#ff6b6b"
            elif task.due_date < date.today():
                date_str = task.due_date.strftime("%d/%m")
                color = "#ff6b6b"
            else:
                date_str = task.due_date.strftime("%d/%m")
                color = "#888888"
        else:
            date_str = ""
            color = "#888888"
            
        if date_str:
            date_label = QLabel(date_str)
            date_label.setStyleSheet(f"color: {color}; font-size: 9pt; background: transparent;")
            date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            right_layout.addWidget(date_label)
            flag_label.setStyleSheet(f"color: {color}; background: transparent;")
        else:
            flag_label.setStyleSheet("color: #888888; background: transparent;")
            
        layout.addLayout(right_layout)
        
        container_layout.addStretch(1)
        container_layout.addWidget(self.inner_widget)
        container_layout.addStretch(1)

    def _toggle_completion(self, checked: bool) -> None:
        if not self.parent_page:
            return
        if checked:
            self.parent_page.service.tasks.mark_completed(self.task.id)
        else:
            self.task.status = TaskStatus.TODO
            self.parent_page.service.update_task(self.task.id, self.task)
        self.parent_page.refresh()

    def eventFilter(self, obj, event):
        if obj == self.inner_widget:
            if event.type() == QEvent.Type.Enter:
                self.inner_widget.setStyleSheet(self.hover_style)

            elif event.type() == QEvent.Type.Leave:
                self.inner_widget.setStyleSheet(self.normal_style)

            elif event.type() == QEvent.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.LeftButton:
                    if self.parent_page and hasattr(self.parent_page, "edit_task"):
                        self.parent_page.edit_task(self.task.id)

        return super().eventFilter(obj, event)


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
            id=self.original_task.id if self.original_task else None
        )


class TasksPage(QWidget):
    def __init__(self, service: ProductivityService) -> None:
        super().__init__()
        self.service = service
        self._selected_task_id: int | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Toolbar
        self.toolbar = ToolBar()
        layout.addWidget(self.toolbar)

        # Task list
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

        # Connections
        self.toolbar.add_button.clicked.connect(self.add_task)

    def refresh(self) -> None:
        tasks = self.service.tasks.list()
        self.list_widget.clear()
        for task in tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            widget = TaskItemWidget(task, parent=self)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
        if tasks and self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)

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
