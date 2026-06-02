from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
)
from PySide6.QtCore import Qt, Signal, QSize

class Sidebar(QFrame):
    nav_changed = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setObjectName("SideBar")

        self.expanded_width = 220
        self.collapsed_width = 60
        self.collapsed = False

        self.setFixedWidth(self.expanded_width)

        side_layout = QVBoxLayout(self)
        side_layout.setContentsMargins(12, 20, 12, 20)
        side_layout.setSpacing(14)

        # ── Header ──────────────────────────────────────────────
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.toggle_btn = QPushButton()
        self.toggle_btn.setFixedSize(32, 32)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.11);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.16);
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)

        header.addStretch()
        header.addWidget(self.toggle_btn)

        side_layout.addLayout(header)

        # ── Navigation ──────────────────────────────────────────
        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setFocusPolicy(Qt.NoFocus)
        self.nav.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                color: rgba(255, 255, 255, 0.6);
                border-radius: 8px;
                padding: 8px 10px;
                margin: 1px 0px;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.06);
                color: rgba(255, 255, 255, 0.85);
            }
            QListWidget::item:selected {
                background: rgba(255, 255, 255, 0.10);
                color: white;
            }
        """)

        item = QListWidgetItem("Today")
        item.setTextAlignment(Qt.AlignCenter)
        self.nav.addItem(item)

        side_layout.addWidget(self.nav, 1)

        # no addStretch or extra button at the bottom

        self.nav.currentRowChanged.connect(self.nav_changed.emit)
        self.nav.setCurrentRow(0)

    def setup_icons(self):
        """Call this after QApplication is created."""
        self._set_toggle_icon(collapsed=False)

    def _make_icon(self, svg_bytes: bytes, size: int = 18) -> QIcon:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        renderer = QSvgRenderer(svg_bytes)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)

    def _set_toggle_icon(self, collapsed: bool):
        if collapsed:
            # ">>" — pointing right to indicate "expand"
            svg = b"""
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M5.5 4.5L9.5 9L5.5 13.5" stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M9.5 4.5L13.5 9L9.5 13.5" stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            """
        else:
            # "< >" — the code bracket icon from image 2
            svg = b"""
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M7 5L3 9L7 13" stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M11 5L15 9L11 13" stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            """
        self.toggle_btn.setIcon(self._make_icon(svg))
        self.toggle_btn.setIconSize(QSize(18, 18))

    def toggle_sidebar(self):
        self.collapsed = not self.collapsed

        if self.collapsed:
            self.setFixedWidth(self.collapsed_width)
            self.nav.item(0).setText("☀")
            self.nav.item(0).setTextAlignment(Qt.AlignCenter)
            self._set_toggle_icon(collapsed=True)

            # Collapsed: center the icon, remove horizontal padding so it fits
            self.nav.setStyleSheet("""
                QListWidget {
                    background: transparent;
                    border: none;
                    outline: none;
                }
                QListWidget::item {
                    color: rgba(255, 255, 255, 0.6);
                    border-radius: 8px;
                    padding: 8px 0px;
                    margin: 1px 4px;
                }
                QListWidget::item:hover {
                    background: rgba(255, 255, 255, 0.06);
                    color: rgba(255, 255, 255, 0.85);
                }
                QListWidget::item:selected {
                    background: rgba(255, 255, 255, 0.10);
                    color: white;
                }
            """)

        else:
            self.setFixedWidth(self.expanded_width)
            self.nav.item(0).setText("☀ Today")
            self.nav.item(0).setTextAlignment(Qt.AlignCenter)
            self._set_toggle_icon(collapsed=False)

            # Expanded: restore normal padding
            self.nav.setStyleSheet("""
                QListWidget {
                    background: transparent;
                    border: none;
                    outline: none;
                }
                QListWidget::item {
                    color: rgba(255, 255, 255, 0.6);
                    border-radius: 8px;
                    padding: 8px 10px;
                    margin: 1px 0px;
                }
                QListWidget::item:hover {
                    background: rgba(255, 255, 255, 0.06);
                    color: rgba(255, 255, 255, 0.85);
                }
                QListWidget::item:selected {
                    background: rgba(255, 255, 255, 0.10);
                    color: white;
                }
            """)

    def set_current_row(self, row: int) -> None:
        """Set the current navigation row (snake_case API used by MainWindow)."""
        self.nav.setCurrentRow(row)