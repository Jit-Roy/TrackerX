from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtCore import QDate, QSize, Qt
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


class ToolBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)

        # Add button
        self.add_button = QPushButton()
        self.add_button.setToolTip("Add Task")
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.setFixedSize(44, 44)

        self.add_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 22px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
                border: none;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.15);
                border: none;
            }
        """)

        layout.addStretch()
        layout.addWidget(self.add_button)
        layout.addStretch()

        self.setup_icons()

    def setup_icons(self):
        icon_svg = b"""
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 2.5V13.5M2.5 8H13.5"
                  stroke="#ffffff"
                  stroke-width="1.75"
                  stroke-linecap="round"/>
        </svg>
        """

        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        svg_renderer = QSvgRenderer(icon_svg)
        painter = QPainter(pixmap)
        painter.setOpacity(0.9)
        svg_renderer.render(painter)
        painter.end()

        self.add_button.setIcon(QIcon(pixmap))
        self.add_button.setIconSize(QSize(16, 16))