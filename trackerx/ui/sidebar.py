from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize, QEasingCurve, QVariantAnimation
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


# ── All-white SVG icon definitions ──────────────────────────────────────────
# Every stroke/fill is pure white — no colour emojis, no platform-dependent glyphs.

_ICON_SUN = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none">
  <circle cx="10" cy="10" r="3.4" stroke="white" stroke-width="1.55"/>
  <line x1="10" y1="1.8" x2="10" y2="3.8"  stroke="white" stroke-width="1.55" stroke-linecap="round"/>
  <line x1="10" y1="16.2" x2="10" y2="18.2" stroke="white" stroke-width="1.55" stroke-linecap="round"/>
  <line x1="1.8" y1="10" x2="3.8"  y2="10"  stroke="white" stroke-width="1.55" stroke-linecap="round"/>
  <line x1="16.2" y1="10" x2="18.2" y2="10" stroke="white" stroke-width="1.55" stroke-linecap="round"/>
  <line x1="4.05" y1="4.05" x2="5.47" y2="5.47" stroke="white" stroke-width="1.55" stroke-linecap="round"/>
  <line x1="14.53" y1="14.53" x2="15.95" y2="15.95" stroke="white" stroke-width="1.55" stroke-linecap="round"/>
  <line x1="15.95" y1="4.05" x2="14.53" y2="5.47" stroke="white" stroke-width="1.55" stroke-linecap="round"/>
  <line x1="5.47" y1="14.53" x2="4.05" y2="15.95" stroke="white" stroke-width="1.55" stroke-linecap="round"/>
</svg>"""

_ICON_HABITS = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none">
  <path d="M16.5 10A6.5 6.5 0 1 1 10 3.5" stroke="white" stroke-width="1.55" stroke-linecap="round"/>
  <polyline points="10,1 10,5 14,5" stroke="white" stroke-width="1.55"
            stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

_ICON_CALENDAR = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none">
  <rect x="2.5" y="4.5" width="15" height="13" rx="2.5"
        stroke="white" stroke-width="1.55"/>
  <line x1="2.5" y1="9"   x2="17.5" y2="9"   stroke="white" stroke-width="1.55"/>
  <line x1="7"   y1="2.2" x2="7"    y2="5.5"  stroke="white" stroke-width="1.55" stroke-linecap="round"/>
  <line x1="13"  y1="2.2" x2="13"   y2="5.5"  stroke="white" stroke-width="1.55" stroke-linecap="round"/>
  <circle cx="7"  cy="12.5" r="1.0" fill="white"/>
  <circle cx="10" cy="12.5" r="1.0" fill="white"/>
  <circle cx="13" cy="12.5" r="1.0" fill="white"/>
  <circle cx="7"  cy="15.5" r="1.0" fill="white"/>
  <circle cx="10" cy="15.5" r="1.0" fill="white"/>
</svg>"""

_ICON_PROJECTS = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none">
  <path d="M4 7.5H16" stroke="white" stroke-width="1.55" stroke-linecap="round"/>
  <rect x="3" y="7.5" width="14" height="9" rx="2" stroke="white" stroke-width="1.55"/>
  <path d="M7 7.5V5.5H13V7.5" stroke="white" stroke-width="1.55" stroke-linecap="round"/>
</svg>"""

# Toggle chevrons
_ICON_CHEVRONS_LEFT = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none">
  <path d="M12 5.5L8 10L12 14.5" stroke="white" stroke-width="1.6"
        stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M16 5.5L12 10L16 14.5" stroke="white" stroke-width="1.6"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

_ICON_CHEVRONS_RIGHT = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none">
  <path d="M8 5.5L12 10L8 14.5" stroke="white" stroke-width="1.6"
        stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M4 5.5L8 10L4 14.5" stroke="white" stroke-width="1.6"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

# Ordered nav item registry — index is stable and maps to nav rows
_NAV_REGISTRY: list[tuple[bytes, str]] = [
    (_ICON_SUN,      "Recent"),
    (_ICON_HABITS,   "Habits"),
    (_ICON_CALENDAR, "Planner"),
    (_ICON_PROJECTS, "Projects"),
]


class Sidebar(QFrame):
    nav_changed = Signal(int)

    EXPANDED_W  = 220
    COLLAPSED_W = 64

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SideBar")
        self.collapsed = False

        # Pin to expanded width (both min & max so layout respects it)
        self.setFixedWidth(self.EXPANDED_W)

        self.setStyleSheet("""
            QFrame#SideBar {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #121216,
                    stop:1 #0b0b0e
                );
                border-right: 1px solid rgba(255, 255, 255, 0.055);
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 20, 12, 20)
        root.setSpacing(0)

        # ── Header: wordmark + toggle ────────────────────────────
        hdr = QHBoxLayout()
        hdr.setContentsMargins(4, 0, 0, 0)
        hdr.setSpacing(0)

        self.logo_lbl = QLabel("")
        self.logo_lbl.setStyleSheet("""
            color: rgba(255, 255, 255, 0.88);
            font-family: 'SF Pro Display', 'Helvetica Neue', 'Segoe UI', sans-serif;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 4.5px;
        """)

        self.toggle_btn = QPushButton()
        self.toggle_btn.setFixedSize(32, 32)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.09);
                border-color: rgba(255, 255, 255, 0.13);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.14);
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)

        hdr.addWidget(self.logo_lbl)
        hdr.addStretch()
        hdr.addWidget(self.toggle_btn)
        root.addLayout(hdr)
        root.addSpacing(28)

        # ── Section label ────────────────────────────────────────
        self.section_lbl = QLabel("")
        self.section_lbl.setStyleSheet("""
            color: rgba(255, 255, 255, 0.20);
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 2.5px;
            padding-left: 6px;
        """)
        root.addWidget(self.section_lbl)
        root.addSpacing(6)

        # ── Nav list ─────────────────────────────────────────────
        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav.setIconSize(QSize(18, 18))
        self.nav.setSpacing(2)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._apply_nav_style(collapsed=False)
        root.addWidget(self.nav, 1)

        # ── Footer ───────────────────────────────────────────────
        root.addSpacing(10)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.065); border: none;")
        root.addWidget(sep)
        root.addSpacing(12)

        self.footer_lbl = QLabel("v 2 . 0")
        self.footer_lbl.setStyleSheet("""
            color: rgba(255, 255, 255, 0.17);
            font-size: 9px;
            letter-spacing: 2px;
            padding-left: 6px;
        """)
        root.addWidget(self.footer_lbl)

        self.nav.currentRowChanged.connect(self.nav_changed.emit)

    # ── Public entry point ────────────────────────────────────────────────────

    def setup_icons(self) -> None:
        """Call once after QApplication has been created."""
        self._rebuild_nav()
        self._set_toggle_icon(collapsed=False)

    def set_current_row(self, row: int) -> None:
        self.nav.setCurrentRow(row)

    # ── Toggle ────────────────────────────────────────────────────────────────

    def toggle_sidebar(self) -> None:
        self.collapsed = not self.collapsed

        if self.collapsed:
            # Hide textual chrome
            self.logo_lbl.hide()
            self.section_lbl.hide()
            self.footer_lbl.hide()
            # Strip item labels — leave only icons, update size hints
            for i in range(self.nav.count()):
                self.nav.item(i).setText("")
                self.nav.item(i).setSizeHint(QSize(40, 44))
            self._animate_width(self.COLLAPSED_W)
        else:
            # Restore item labels and size hints
            for i, (_, label) in enumerate(_NAV_REGISTRY):
                if i < self.nav.count():
                    self.nav.item(i).setText(f"  {label}")
                    self.nav.item(i).setSizeHint(QSize(180, 44))
            self.logo_lbl.show()
            self.section_lbl.show()
            self.footer_lbl.show()
            self._animate_width(self.EXPANDED_W)

        self._apply_nav_style(collapsed=self.collapsed)
        self._set_toggle_icon(collapsed=self.collapsed)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _rebuild_nav(self) -> None:
        self.nav.clear()
        for svg, label in _NAV_REGISTRY:
            icon = self._svg_icon(svg)
            item = QListWidgetItem(icon, f"  {label}")
            size = QSize(40, 44) if self.collapsed else QSize(180, 44)
            item.setSizeHint(size)
            self.nav.addItem(item)
        self.nav.setCurrentRow(0)

    def _svg_icon(self, svg_bytes: bytes, size: int = 18) -> QIcon:
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(svg_bytes)
        painter = QPainter(px)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()
        return QIcon(px)

    def _set_toggle_icon(self, collapsed: bool) -> None:
        svg = _ICON_CHEVRONS_RIGHT if collapsed else _ICON_CHEVRONS_LEFT
        self.toggle_btn.setIcon(self._svg_icon(svg))
        self.toggle_btn.setIconSize(QSize(18, 18))

    def _apply_nav_style(self, collapsed: bool) -> None:
        if collapsed:
            item_padding = "padding: 8px 3px;"
            item_margin  = "margin: 2px 4px;"
        else:
            item_padding = "padding: 10px 10px 10px 14px;"
            item_margin  = "margin: 2px 0px;"

        self.nav.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                color: rgba(255, 255, 255, 0.38);
                border-radius: 10px;
                {item_padding}
                {item_margin}
                font-size: 13px;
                font-weight: 500;
                letter-spacing: 0.3px;
            }}
            QListWidget::item:hover {{
                background: rgba(255, 255, 255, 0.055);
                color: rgba(255, 255, 255, 0.78);
            }}
            QListWidget::item:selected {{
                background: rgba(255, 255, 255, 0.10);
                color: rgba(255, 255, 255, 0.95);
            }}
            QListWidget {{
                show-decoration-selected: 1;
            }}
            QAbstractScrollArea {{
                margin: 0;
                padding: 0;
                background: transparent;
            }}
        """)

    def _animate_width(self, target: int) -> None:
        """Smooth width transition using QVariantAnimation (no fixed-width lock needed)."""
        anim = QVariantAnimation(self)
        anim.setStartValue(self.width())
        anim.setEndValue(target)
        anim.setDuration(240)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(
            lambda v: self.setFixedWidth(int(v))  # type: ignore[arg-type]
        )
        anim.start(QVariantAnimation.DeletionPolicy.DeleteWhenStopped)
        self._anim = anim  # keep a reference so GC doesn't destroy it mid-flight