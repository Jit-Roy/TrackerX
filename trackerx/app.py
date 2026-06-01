from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QStyle, QSystemTrayIcon

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
        self.window = MainWindow(self.service)
        self.tray = QSystemTrayIcon()
        self.tray.setToolTip("TrackerX")
        tray_icon = self._build_tray_icon()
        if not tray_icon.isNull():
            self.tray.setIcon(tray_icon)
        if QSystemTrayIcon.isSystemTrayAvailable() and not self.tray.icon().isNull():
            self.tray.show()
        self.apply_theme(self.service.get_setting("theme", "dark"))

    def _build_tray_icon(self) -> QIcon:
        style_icon = self.qt_app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        if not style_icon.isNull():
            return style_icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.blue)
        return QIcon(pixmap)

    def apply_theme(self, mode: str) -> None:
        self.service.set_setting("theme", mode)
        self.qt_app.setStyleSheet(DARK_THEME if mode == "dark" else LIGHT_THEME)

    def run(self) -> int:
        # Call setup_icons now that QApplication exists
        self.window.sidebar.setup_icons()
        self.window.today.toolbar.setup_icons()
        self.window.show()
        return self.qt_app.exec()
