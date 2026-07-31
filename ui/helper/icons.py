from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

ORBIT_LOGO_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <defs>
    <clipPath id="needleClip">
      <circle cx="512" cy="512" r="415"/>
    </clipPath>
  </defs>
  <circle cx="512" cy="512" r="450" fill="none" stroke="#ffffff" stroke-width="44"/>
  <g clip-path="url(#needleClip)">
    <g transform="rotate(-45 512 512)">
      <polygon points="912,512 512,462 512,562" fill="#ffffff" stroke="#ffffff" stroke-width="13" stroke-linejoin="bevel"/>
      <polygon points="112,512 512,462 512,562" fill="none" stroke="#ffffff" stroke-width="13" stroke-linejoin="bevel"/>
      <line x1="112" y1="512" x2="512" y2="512" stroke="#ffffff" stroke-width="7" stroke-linecap="round"/>
    </g>
  </g>
  <circle cx="512" cy="512" r="68" fill="none" stroke="#ffffff" stroke-width="16"/>
  <circle cx="512" cy="512" r="42" fill="#ffffff"/>
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
