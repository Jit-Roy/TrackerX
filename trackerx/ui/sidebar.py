from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QListWidget, QVBoxLayout


class Sidebar(QFrame):
    nav_changed = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SideBar")
        
        side_layout = QVBoxLayout(self)
        side_layout.setContentsMargins(16, 20, 16, 20)
        side_layout.setSpacing(14)

        brand = QLabel("TrackerX")
        brand.setObjectName("Brand")
        side_layout.addWidget(brand)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.addItems(["Today"])
        self.nav.setFixedWidth(220)
        side_layout.addWidget(self.nav, 1)
        
        self.nav.currentRowChanged.connect(self.nav_changed.emit)
        
    def set_current_row(self, index: int) -> None:
        self.nav.setCurrentRow(index)