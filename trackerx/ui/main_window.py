from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from .helper.icons import build_orbit_icon
from ..core.services import ProductivityService
from .recent import TasksPage
from .habit import HabitPage
from .planner import PlannerPage
from .diary import DiaryPage
from .project import ProjectPage
from .helper.sidebar import Sidebar


class MainWindow(QMainWindow):
    def __init__(self, service: ProductivityService) -> None:
        super().__init__()
        self.service = service
        self.setWindowTitle("TrackerX")
        self.setWindowIcon(build_orbit_icon(128))
        self.resize(1520, 960)
        self._build_ui()
        self._wire_services()

    def _build_ui(self) -> None:
        container = QWidget()
        root = QHBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.nav_changed.connect(self._on_nav_changed)

        self.stack = QStackedWidget()
        self.today = TasksPage(self.service)
        self.habits = HabitPage(self.service)
        self.planner = PlannerPage(self.service)
        self.diary = DiaryPage(self.service)
        self.projects = ProjectPage(self.service)

        for page in [self.today, self.habits, self.planner, self.diary, self.projects]:
            self.stack.addWidget(page)

        root.addWidget(self.sidebar)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(container)
        self.sidebar.set_current_row(0)

    def _wire_services(self) -> None:
        self.service.bootstrap()
        self.service.refresh_overdue_tasks()

    def refresh_all(self) -> None:
        for page in [self.today, self.habits, self.planner, self.diary, self.projects]:
            if hasattr(page, "refresh"):
                page.refresh()

    def _on_nav_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        current_page = self.stack.currentWidget()
        if hasattr(current_page, "refresh"):
            current_page.refresh()
