from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

ORBIT_LOGO_SVG = b"""<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"
fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\">
  <circle cx=\"12\" cy=\"12\" r=\"2\"/>
  <ellipse cx=\"12\" cy=\"12\" rx=\"8\" ry=\"3\"/>
  <ellipse cx=\"12\" cy=\"12\" rx=\"3\" ry=\"8\"/>
</svg>"""


def build_orbit_icon(size: int = 24) -> QIcon:
    icon = QIcon()
    for s in [16, 24, 32, 48, 64, 128, 256]:
        pixmap = QPixmap(s, s)
        pixmap.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(ORBIT_LOGO_SVG)
        painter = QPainter(pixmap)
        renderer.render(painter, QRectF(0, 0, s, s))
        painter.end()
        icon.addPixmap(pixmap)
    return icon
