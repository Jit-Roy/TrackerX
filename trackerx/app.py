from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from .ui.icons import build_orbit_icon

from .config import APP_PATHS
from .core.database import Database
from .core.services import ProductivityService
from .core.theme import DARK_THEME, LIGHT_THEME
from .ui.main_window import MainWindow


class TrackerXApp:
    def __init__(self) -> None:
        self.qt_app = QApplication([])
        self.qt_app.setApplicationName("TrackerX")
        self.qt_app.setOrganizationName("TrackerX")
        self.database = Database(APP_PATHS.database_path)
        self.service = ProductivityService(self.database)
        self.app_icon = build_orbit_icon(256)
        self.qt_app.setWindowIcon(self.app_icon)
        self.window = MainWindow(self.service)
        self.window.setWindowIcon(self.app_icon)

        self.tray = QSystemTrayIcon()
        self.tray.setToolTip("TrackerX")
        self.tray.setIcon(self._build_tray_icon())
        if QSystemTrayIcon.isSystemTrayAvailable() and not self.tray.icon().isNull():
            self.tray.show()
        self.apply_theme(self.service.get_setting("theme", "dark"))

    def _build_tray_icon(self) -> QIcon:
        return build_orbit_icon(16)

    def apply_theme(self, mode: str) -> None:
        self.service.set_setting("theme", mode)
        self.qt_app.setStyleSheet(DARK_THEME if mode == "dark" else LIGHT_THEME)

    def run(self) -> int:
        # Call setup_icons now that QApplication exists
        self.window.sidebar.setup_icons()
        self.window.today.toolbar.setup_icons()
        self.window.show()
        return self.qt_app.exec()
