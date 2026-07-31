from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget
from PySide6.QtCore import QSettings
from PySide6.QtGui import QCloseEvent

from .helper.icons import build_orbit_icon
from core.services import ProductivityService
from .recent import TasksPage
from .habit import HabitPage
from .planner import PlannerPage
from .diary import DiaryPage
from .notes import NotesPage
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
        self._restore_state()

    def _restore_state(self) -> None:
        settings = QSettings("Jit-Roy", "TrackerX")
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))
        if settings.contains("windowState"):
            self.restoreState(settings.value("windowState"))

    def closeEvent(self, event: QCloseEvent) -> None:
        settings = QSettings("Jit-Roy", "TrackerX")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_dwm_titlebar()

    def _apply_dwm_titlebar(self):
        import sys
        if sys.platform != "win32":
            return
            
        try:
            import ctypes
            from ctypes import c_int
            
            hwnd = int(self.winId())
            
            # Match the top of the sidebar gradient (#121216)
            color = 0x00161212
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(c_int(color)), ctypes.sizeof(c_int))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_TEXT_COLOR, ctypes.byref(c_int(color)), ctypes.sizeof(c_int))
                
            try:
                from .helper.win32_utils import hide_titlebar_icon
                hide_titlebar_icon(hwnd)
            except Exception:
                pass
                
        except Exception:
            pass

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
        self.notes = NotesPage(self.service)
        self.projects = ProjectPage(self.service)

        for page in [self.today, self.habits, self.planner, self.diary, self.notes, self.projects]:
            self.stack.addWidget(page)

        root.addWidget(self.sidebar)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(container)
        self.sidebar.set_current_row(0)

    def _wire_services(self) -> None:
        self.service.bootstrap()
        self.service.refresh_overdue_tasks()

    def refresh_all(self) -> None:
        for page in [self.today, self.habits, self.planner, self.diary, self.notes, self.projects]:
            if hasattr(page, "refresh"):
                page.refresh()

    def _on_nav_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        current_page = self.stack.currentWidget()
        if hasattr(current_page, "on_navigated_to"):
            current_page.on_navigated_to()
        elif hasattr(current_page, "refresh"):
            current_page.refresh()
