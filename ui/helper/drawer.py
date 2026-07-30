from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    Signal,
    Property,
)
from PySide6.QtGui import QColor, QPainter, QPen, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SlideOutDrawer(QFrame):
    """
    A reusable slide-out drawer that sits side-by-side with its sibling widgets.
    It animates its fixedWidth from 0 to its target width.
    """
    
    closed = Signal()

    def __init__(self, title: str = "", width: int = 400, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.drawer_width = width
        self.is_open = False
        
        self.setObjectName("DrawerPanel")
        self.setStyleSheet(
            "QFrame#DrawerPanel { "
            "   background: qlineargradient("
            "       x1:0, y1:0, x2:0, y2:1,"
            "       stop:0 #121216,"
            "       stop:1 #0b0b0e"
            "   );"
            "   border-left: 1px solid rgba(255, 255, 255, 0.055); "
            "}"
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        # Start fully closed
        self.setFixedWidth(0)

        # Layout for panel
        self.panel_layout = QVBoxLayout(self)
        self.panel_layout.setContentsMargins(0, 0, 0, 0)
        self.panel_layout.setSpacing(0)

        # Header
        self.header = QWidget()
        self.header.setStyleSheet("background: transparent;")
        self.header.setFixedHeight(60)
        # We need a minimum width for the header so its contents don't squish weirdly when animating
        self.header.setMinimumWidth(width)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #e8e8ed; font-size: 14pt; font-weight: 600;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.close_btn = QPushButton()
        self.close_btn.setIcon(self._create_close_icon())
        self.close_btn.setIconSize(QSize(16, 16))
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); border-radius: 16px; }"
        )
        self.close_btn.clicked.connect(self.close_drawer)
        header_layout.addWidget(self.close_btn)

        self.panel_layout.addWidget(self.header)

        # Content container
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_widget.setMinimumWidth(width)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(24, 16, 24, 24)
        self.content_layout.setSpacing(16)
        
        self.panel_layout.addWidget(self.content_widget, 1)

        # Animation
        self.animation = QPropertyAnimation(self, b"animatedWidth")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self._on_animation_finished)

    def _get_animated_width(self) -> int:
        return self.width()
        
    def _set_animated_width(self, w: int) -> None:
        self.setFixedWidth(w)
        
    animatedWidth = Property(int, _get_animated_width, _set_animated_width)

    def _create_close_icon(self) -> QIcon:
        pix = QPixmap(24, 24)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#a0a0a5"))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawLine(6, 6, 18, 18)
        p.drawLine(18, 6, 6, 18)
        p.end()
        return QIcon(pix)

    def set_content(self, widget: QWidget) -> None:
        """Replace the drawer's content with the given widget."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.addWidget(widget)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def open_drawer(self) -> None:
        if self.is_open:
            return
        self.is_open = True
        
        self.animation.stop()
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(self.drawer_width)
        self.animation.start()

    def close_drawer(self) -> None:
        if not self.is_open:
            return
        self.is_open = False
        
        self.animation.stop()
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(0)
        self.animation.start()

    def _on_animation_finished(self) -> None:
        if not self.is_open:
            self.closed.emit()
