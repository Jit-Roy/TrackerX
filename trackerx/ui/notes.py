"""
Notes page
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal, QSize, QByteArray
from PySide6.QtGui import (
    QAction, QBrush, QColor, QFont, QPainter, QPen, QPixmap, QIcon,
    QTextBlockFormat, QTextCursor,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.models import NoteNode
from ..core.services import ProductivityService


# ── Palette ───────────────────────────────────────────────────────────────────
_LEFT_BG   = "#111111"   # left panel
_RIGHT_BG  = "#0a0a0a"   # right editor panel
_HDR_BG    = "#111111"
_SEARCH_BG = "#1a1a1a"
_SEL_BG    = "rgba(255,255,255,0.12)"
_HOV_BG    = "rgba(255,255,255,0.04)"
_LINE_COL  = QColor(65, 65, 65)      # tree connector lines
_DIVIDER   = "rgba(255,255,255,0.07)"
_T_PRI     = "#ffffff"
_T_SEC     = "#9a9a9a"
_T_TER     = "#555555"
_T_DIM     = "#333333"
_BORDER    = "rgba(255,255,255,0.08)"
_MONO      = "Courier New"

# Layout constants
_LEFT_W      = 280
_AUTOSAVE_MS = 850
_INDENT_PX   = 18    # px per depth level
_TREE_LEFT   = 10    # fixed left margin before depth-0 content
_CHV_W       = 16    # chevron button width


# ── SVG helpers ───────────────────────────────────────────────────────────────

_SVG_CHEVRON_RIGHT = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
  <polyline points="3,2 7,5 3,8" fill="none" stroke="white"
            stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" opacity="0.45"/>
</svg>"""

_SVG_CHEVRON_DOWN = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
  <polyline points="2,3.5 5,7 8,3.5" fill="none" stroke="white"
            stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" opacity="0.45"/>
</svg>"""

_SVG_SEARCH = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none">
  <circle cx="6.5" cy="6.5" r="4.5" stroke="white" stroke-width="1.3" opacity="0.4"/>
  <line x1="10" y1="10" x2="14" y2="14" stroke="white" stroke-width="1.3"
        stroke-linecap="round" opacity="0.4"/>
</svg>"""

_SVG_MENU = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none">
  <line x1="2" y1="4"  x2="14" y2="4"  stroke="white" stroke-width="1.4" stroke-linecap="round" opacity="0.6"/>
  <line x1="2" y1="8"  x2="14" y2="8"  stroke="white" stroke-width="1.4" stroke-linecap="round" opacity="0.6"/>
  <line x1="2" y1="12" x2="14" y2="12" stroke="white" stroke-width="1.4" stroke-linecap="round" opacity="0.6"/>
</svg>"""

_SVG_PLUS = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 14" fill="none">
  <line x1="7" y1="2" x2="7" y2="12" stroke="white" stroke-width="1.5" stroke-linecap="round" opacity="0.7"/>
  <line x1="2" y1="7" x2="12" y2="7" stroke="white" stroke-width="1.5" stroke-linecap="round" opacity="0.7"/>
</svg>"""

_SVG_TRASH = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 14" fill="none">
  <path d="M4.5,3 L9.5,3 M2,4.5 L12,4.5 M3.5,4.5 L4.5,12 C4.5,12.5 5,13 5.5,13 L8.5,13 C9,13 9.5,12.5 9.5,12 L10.5,4.5 M6,6.5 L6,10.5 M8,6.5 L8,10.5" stroke="white" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/>
</svg>"""


def _svg_icon(svg_bytes: bytes, size: int) -> QIcon:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    r = QSvgRenderer(QByteArray(svg_bytes))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p)
    p.end()
    return QIcon(px)


def _svg_pixmap(svg_bytes: bytes, size: int) -> QPixmap:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    r = QSvgRenderer(QByteArray(svg_bytes))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p)
    p.end()
    return px


# ── Dividers ──────────────────────────────────────────────────────────────────

def _hdiv(color: str = _DIVIDER) -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background: {color}; border: none;")
    return f


def _vdiv(color: str = _DIVIDER) -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setFixedWidth(1)
    f.setStyleSheet(f"background: {color}; border: none;")
    return f


# ── Toast Notification ────────────────────────────────────────────────────────

class _Toast(QWidget):
    undo_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(
            f"background: #1e1e1e; border: 1px solid {_BORDER}; border-radius: 8px;"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)

        self.lbl = QLabel("Note deleted.")
        self.lbl.setStyleSheet(f"color: {_T_PRI}; font-size: 9pt; background: transparent; border: none;")
        lay.addWidget(self.lbl)

        lay.addSpacing(16)

        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.undo_btn.setStyleSheet(
            f"QPushButton {{ color: #4DAAFB; font-weight: bold; font-size: 9pt; background: transparent; border: none; padding: 4px; }}"
            f"QPushButton:hover {{ color: #7BC0FF; text-decoration: underline; }}"
        )
        self.undo_btn.clicked.connect(self.undo_requested.emit)
        lay.addWidget(self.undo_btn)

        self.hide()

    def reposition(self) -> None:
        if self.parent():
            pw = self.parent().width()
            ph = self.parent().height()
            self.adjustSize()
            self.move((pw - self.width()) // 2, ph - self.height() - 32)


# ── Tree node row ─────────────────────────────────────────────────────────────

class _NodeRow(QWidget):
    """
    One row in the infinite tree sidebar.

    Renders its own background + tree connector lines via paintEvent.
    Layout: [indentation with tree lines][chevron or spacer][title]

    Signals:
      node_clicked(int)    – left-click on row body → select node
      toggle_expand(int)   – click on chevron arrow → expand/collapse
      add_child_req(int)   – context menu "Add sub-page"
      rename_req(int)      – context menu "Rename"
      delete_req(int)      – context menu "Delete"
    """

    node_clicked   = Signal(int)
    toggle_expand  = Signal(int)
    add_child_req  = Signal(int)
    rename_req     = Signal(int)
    delete_req     = Signal(int)

    def __init__(
        self,
        node_id: int,
        title: str,
        depth: int,
        has_children: bool,
        is_expanded: bool,
        is_selected: bool,
        continues: list[bool],   # continues[i] = True if ancestor at depth i has more siblings
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.node_id     = node_id
        self._selected   = is_selected
        self._hovered    = False
        self._depth      = depth
        self._continues  = continues

        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

        # Content starts after indentation
        content_x = _TREE_LEFT + depth * _INDENT_PX

        lay = QHBoxLayout(self)
        lay.setContentsMargins(content_x, 0, 6, 0)
        lay.setSpacing(0)

        # Chevron button (expand/collapse) — only for nodes with children
        self._chv = QPushButton()
        self._chv.setFixedSize(_CHV_W, _CHV_W)
        self._chv.setFlat(True)
        self._chv.setStyleSheet(
            "QPushButton { background: transparent; border: none; padding: 0; }"
        )
        if has_children:
            icon_svg = _SVG_CHEVRON_DOWN if is_expanded else _SVG_CHEVRON_RIGHT
            self._chv.setIcon(_svg_icon(icon_svg, 10))
            self._chv.setIconSize(QSize(10, 10))
            self._chv.setCursor(Qt.CursorShape.PointingHandCursor)
            self._chv.clicked.connect(lambda: self.toggle_expand.emit(node_id))
        else:
            # Leaf: invisible spacer (same width so text aligns)
            self._chv.setEnabled(False)
            self._chv.setCursor(Qt.CursorShape.ArrowCursor)
        lay.addWidget(self._chv)
        lay.addSpacing(4)

        # Title label (transparent to mouse events → parent catches them)
        self._lbl = QLabel(title)
        font = self._lbl.font()
        font.setPointSize(9)
        self._lbl.setFont(font)
        self._lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._lbl.setStyleSheet(f"color: {_T_PRI}; background: transparent;")
        lay.addWidget(self._lbl, 1)

        # Actions wrapper (+ and Trash)
        self._actions_wrap = QWidget()
        self._actions_wrap.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        al = QHBoxLayout(self._actions_wrap)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(2)

        # Add sub-page button
        self._add_btn = QPushButton()
        self._add_btn.setIcon(_svg_icon(_SVG_PLUS, 11))
        self._add_btn.setIconSize(QSize(11, 11))
        self._add_btn.setFixedSize(22, 22)
        self._add_btn.setFlat(True)
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setToolTip("Add sub-page")
        self._add_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 4px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.12); }"
        )
        self._add_btn.clicked.connect(lambda: self.add_child_req.emit(self.node_id))
        al.addWidget(self._add_btn)

        # Delete button
        self._del_btn = QPushButton()
        self._del_btn.setIcon(_svg_icon(_SVG_TRASH, 12))
        self._del_btn.setIconSize(QSize(12, 12))
        self._del_btn.setFixedSize(22, 22)
        self._del_btn.setFlat(True)
        self._del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._del_btn.setToolTip("Delete page")
        self._del_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 4px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.12); }"
        )
        self._del_btn.clicked.connect(lambda: self.delete_req.emit(self.node_id))
        al.addWidget(self._del_btn)

        self._actions_wrap.hide()
        lay.addWidget(self._actions_wrap)

    # ── Paint: background + tree connector lines ───────────────────────────

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()
        H = self.height()

        # 1. Background
        if self._selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 30)))
            painter.drawRoundedRect(2, 1, W - 4, H - 2, 5, 5)
            # Left accent bar
            painter.setBrush(QBrush(QColor(255, 255, 255, 180)))
            painter.drawRoundedRect(2, 4, 2, H - 8, 1, 1)
        elif self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 12)))
            painter.drawRoundedRect(2, 1, W - 4, H - 2, 5, 5)

        # 2. Tree connector lines (only for depth > 0)
        if self._depth > 0:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            pen = QPen(_LINE_COL, 1)
            pen.setCosmetic(True)
            painter.setPen(pen)

            mid = H // 2

            for i in range(self._depth):
                # Center x of the vertical line for ancestor depth i
                x = _TREE_LEFT + i * _INDENT_PX + _INDENT_PX // 2

                if i < self._depth - 1:
                    # Ancestor column: draw full vertical line if it continues
                    if i < len(self._continues) and self._continues[i]:
                        painter.drawLine(x, 0, x, H)
                else:
                    # Direct parent column: draw L-connector
                    # Top half of vertical (always — connects from parent above)
                    painter.drawLine(x, 0, x, mid)
                    # Bottom half — only if there are more siblings after this
                    if i < len(self._continues) and self._continues[i]:
                        painter.drawLine(x, mid, x, H)
                    # Horizontal connector to item
                    painter.drawLine(x, mid, x + _INDENT_PX // 2 + 2, mid)

        painter.end()

    # ── Hover / selection style ────────────────────────────────────────────

    def set_selected(self, val: bool) -> None:
        self._selected = val
        self.update()

    def enterEvent(self, _) -> None:
        self._hovered = True
        self._actions_wrap.show()
        self.update()

    def leaveEvent(self, _) -> None:
        self._hovered = False
        self._actions_wrap.hide()
        self.update()

    # ── Click handling ────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.node_clicked.emit(self.node_id)
        super().mousePressEvent(event)

    # ── Context menu ──────────────────────────────────────────────────────

    def _show_menu(self, pos) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #1c1c1c; color: #e8e8ed;"
            f"  border: 1px solid {_BORDER}; border-radius: 8px; padding: 4px; font-size: 9pt; }}"
            "QMenu::item { padding: 6px 18px; border-radius: 5px; }"
            "QMenu::item:selected { background: rgba(255,255,255,0.10); }"
            f"QMenu::separator {{ height: 1px; background: {_DIVIDER}; margin: 4px 0; }}"
        )
        menu.addAction("Add sub-page", lambda: self.add_child_req.emit(self.node_id))
        menu.addSeparator()
        menu.addAction("Rename",       lambda: self.rename_req.emit(self.node_id))
        menu.addSeparator()
        menu.addAction("Delete",       lambda: self.delete_req.emit(self.node_id))
        menu.exec(self.mapToGlobal(pos))


# ── Search result row (flat, no tree lines) ───────────────────────────────────

class _SearchRow(QWidget):
    clicked = Signal(int)   # node_id

    def __init__(self, node_id: int, title: str, parent=None) -> None:
        super().__init__(parent)
        self.node_id  = node_id
        self._hovered = False

        self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 8, 0)

        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {_T_PRI}; font-size: 8.5pt; background: transparent;")
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lay.addWidget(lbl, 1)

    def enterEvent(self, _) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, _) -> None:
        self._hovered = False
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hovered:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(255, 255, 255, 12)))
            p.drawRoundedRect(2, 1, self.width() - 4, self.height() - 2, 5, 5)
        p.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.node_id)
        super().mousePressEvent(event)


# ── Left panel ────────────────────────────────────────────────────────────────

class _LeftPanel(QWidget):
    """
    Sidebar with header, search bar, and infinite recursive tree.
    """

    note_selected          = Signal(int)   # node_id or -1
    sidebar_toggle_requested = Signal()    # hamburger clicked → NotesPage toggles visibility
    delete_requested       = Signal(int)   # node_id

    def __init__(self, service: ProductivityService, parent=None) -> None:
        super().__init__(parent)
        self.service    = service
        self._expanded: set[int] = set()
        self._hidden: set[int] = set()
        self._selected: int | None = None
        self._rows: list[_NodeRow] = []
        self._searching = False

        self.setFixedWidth(_LEFT_W)
        self.setStyleSheet(f"background: {_LEFT_BG};")
        self._build()

    # ── Build skeleton ────────────────────────────────────────────────────

    def _build(self) -> None:
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # ── Header ("Notebook"  ≡)
        hdr = QWidget()
        hdr.setFixedHeight(54)
        hdr.setStyleSheet(f"background: {_HDR_BG};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 12, 0)
        hl.setSpacing(8)

        title_lbl = QLabel("Notebook")
        f = title_lbl.font()
        f.setPointSize(16)
        f.setWeight(QFont.Weight.Bold)
        title_lbl.setFont(f)
        title_lbl.setStyleSheet(f"color: {_T_PRI}; background: transparent;")
        hl.addWidget(title_lbl, 1)

        # New page button
        new_btn = QPushButton()
        new_btn.setIcon(_svg_icon(_SVG_PLUS, 13))
        new_btn.setIconSize(QSize(13, 13))
        new_btn.setFixedSize(26, 26)
        new_btn.setFlat(True)
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setToolTip("New root page")
        new_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 5px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); }"
        )
        new_btn.clicked.connect(self._add_root_node)
        hl.addWidget(new_btn)

        # Hamburger → collapse/expand sidebar
        self._menu_btn = QPushButton()
        self._menu_btn.setIcon(_svg_icon(_SVG_MENU, 14))
        self._menu_btn.setIconSize(QSize(14, 14))
        self._menu_btn.setFixedSize(26, 26)
        self._menu_btn.setFlat(True)
        self._menu_btn.setToolTip("Toggle sidebar")
        self._menu_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 5px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); }"
        )
        self._menu_btn.clicked.connect(self.sidebar_toggle_requested.emit)
        hl.addWidget(self._menu_btn)
        root_lay.addWidget(hdr)

        # ── Search bar
        search_wrap = QWidget()
        search_wrap.setFixedHeight(46)
        search_wrap.setStyleSheet(f"background: {_HDR_BG};")
        sl = QHBoxLayout(search_wrap)
        sl.setContentsMargins(12, 6, 12, 6)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search notes")
        self._search.setFixedHeight(30)
        self._search.setStyleSheet(
            f"QLineEdit {{"
            f"  background: {_SEARCH_BG};"
            f"  color: {_T_PRI};"
            f"  border: 1px solid rgba(255,255,255,0.08);"
            f"  border-radius: 7px;"
            f"  padding: 0 8px;"
            f"  font-size: 8.5pt;"
            f"}}"
            f"QLineEdit:focus {{"
            f"  border: 1px solid rgba(255,255,255,0.18);"
            f"}}"
        )
        # Native leading icon — no overlay/positioning needed
        search_action = QAction(_svg_icon(_SVG_SEARCH, 13), "", self._search)
        self._search.addAction(search_action, QLineEdit.ActionPosition.LeadingPosition)

        self._search.textChanged.connect(self._on_search)
        sl.addWidget(self._search)
        root_lay.addWidget(search_wrap)

        root_lay.addWidget(_hdiv())

        # ── Scrollable tree body
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: {_LEFT_BG}; border: none; }}"
            "QScrollBar:vertical { width: 3px; background: transparent; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.08);"
            "  border-radius: 1px; min-height: 20px; }"
            "QScrollBar::add-line, QScrollBar::sub-line { height: 0; }"
            "QScrollBar::add-page, QScrollBar::sub-page { height: 0; }"
        )

        self._body = QWidget()
        self._body.setStyleSheet(f"background: {_LEFT_BG};")
        self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(4, 6, 4, 12)
        self._body_lay.setSpacing(1)
        self._body_lay.addStretch(1)

        self._scroll.setWidget(self._body)
        root_lay.addWidget(self._scroll, 1)

    # ── Search ────────────────────────────────────────────────────────────

    def _on_search(self, text: str) -> None:
        self._searching = bool(text.strip())
        if self._searching:
            results = self.service.search_nodes(text.strip())
            self._render_search_results(results)
        else:
            self.populate(select_node_id=self._selected)

    def _render_search_results(self, nodes: list[NoteNode]) -> None:
        self._clear_body()
        self._rows = []
        visible_nodes = [n for n in nodes if n.id not in self._hidden]

        if not visible_nodes:
            lbl = QLabel("No results")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {_T_DIM}; font-size: 8pt; background: transparent; padding: 20px;")
            self._body_lay.addWidget(lbl)
        else:
            for node in visible_nodes:
                row = _SearchRow(node.id, node.title)
                row.clicked.connect(self._on_node_clicked)
                self._body_lay.addWidget(row)

        self._body_lay.addStretch(1)

    # ── Populate (recursive tree) ─────────────────────────────────────────

    def populate(self, select_node_id: int | None = None) -> None:
        if select_node_id is not None:
            self._selected = select_node_id

        self._clear_body()
        self._rows = []

        roots = [n for n in self.service.get_root_nodes() if n.id not in self._hidden]

        if not roots:
            hint = QLabel("Press  +  to create your first page")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setWordWrap(True)
            hint.setStyleSheet(
                f"color: {_T_DIM}; font-size: 8pt; background: transparent; padding: 30px 16px;"
            )
            self._body_lay.addWidget(hint)
        else:
            self._render_level(roots, depth=0, continues=[])

        self._body_lay.addStretch(1)

    def _clear_body(self) -> None:
        while self._body_lay.count():
            item = self._body_lay.takeAt(0)
            if w := item.widget():
                w.deleteLater()

    def _render_level(
        self,
        nodes: list[NoteNode],
        depth: int,
        continues: list[bool],
    ) -> None:
        """
        Recursively render visible rows.

        `continues[i]` = True  →  ancestor at depth i has more siblings below
                                   the current position, so draw a full vertical
                                   line through this row at that depth column.
        """
        visible_nodes = [n for n in nodes if n.id not in self._hidden]
        for idx, node in enumerate(visible_nodes):
            is_last    = idx == len(visible_nodes) - 1
            has_ch     = self.service.node_has_children(node.id)
            is_exp     = node.id in self._expanded
            is_sel     = node.id == self._selected

            # continues for the current node: ancestors' state + whether THIS
            # node's parent column should continue (i.e., this node is not last)
            node_continues = continues + [not is_last]

            row = _NodeRow(
                node_id=node.id,
                title=node.title,
                depth=depth,
                has_children=has_ch,
                is_expanded=is_exp,
                is_selected=is_sel,
                continues=node_continues,
            )
            row.node_clicked.connect(self._on_node_clicked)
            row.toggle_expand.connect(self._on_toggle_expand)
            row.add_child_req.connect(self._add_child_node)
            row.rename_req.connect(self._rename_node)
            row.delete_req.connect(self._delete_node)

            self._body_lay.addWidget(row)
            self._rows.append(row)

            # Recurse into expanded children
            if is_exp and has_ch:
                children = self.service.get_node_children(node.id)
                # child_continues: same as node_continues (each child knows whether
                # its OWN parent column continues — handled recursively)
                self._render_level(children, depth + 1, node_continues)

    # ── Selection ─────────────────────────────────────────────────────────

    def _on_node_clicked(self, node_id: int) -> None:
        self._selected = node_id
        for row in self._rows:
            row.set_selected(row.node_id == node_id)
        self.note_selected.emit(node_id)

    # ── Expand / collapse ─────────────────────────────────────────────────

    def _on_toggle_expand(self, node_id: int) -> None:
        if node_id in self._expanded:
            self._expanded.discard(node_id)
        else:
            self._expanded.add(node_id)
        self.populate(select_node_id=self._selected)

    # ── CRUD ──────────────────────────────────────────────────────────────

    def _add_root_node(self) -> None:
        node_id = self.service.create_node(NoteNode(title="Untitled"))
        self._selected = node_id
        self.populate()
        self.note_selected.emit(node_id)

    def _add_child_node(self, parent_id: int) -> None:
        self._expanded.add(parent_id)
        node_id = self.service.create_node(NoteNode(title="Untitled", parent_id=parent_id))
        self._selected = node_id
        self.populate()
        self.note_selected.emit(node_id)

    def _rename_node(self, node_id: int) -> None:
        node = self.service.get_node(node_id)
        current = node.title if node else ""
        title, ok = QInputDialog.getText(self, "Rename", "Name:", text=current)
        if ok and title.strip():
            self.service.rename_node(node_id, title.strip())
            self.populate(select_node_id=self._selected)

    def _delete_node(self, node_id: int) -> None:
        self.delete_requested.emit(node_id)

    def hide_node(self, node_id: int) -> None:
        self._hidden.add(node_id)
        # Check if selected node is a descendant of the hidden node.
        if self._selected is not None:
            curr = self.service.get_node(self._selected)
            while curr:
                if curr.id in self._hidden:
                    self._selected = None
                    self.note_selected.emit(-1)
                    break
                curr = self.service.get_node(curr.parent_id) if curr.parent_id else None
        self.populate(select_node_id=self._selected)

    def unhide_node(self, node_id: int) -> None:
        self._hidden.discard(node_id)
        self.populate(select_node_id=self._selected)

    def refresh(self) -> None:
        if not self._searching:
            self.populate(select_node_id=self._selected)


# ── Editor panel ──────────────────────────────────────────────────────────────

class _EditorPanel(QWidget):
    """
    Right panel matching the reference screenshot:

      [Title (editable, large)]           [Last edited: Today, 10:24 AM]
      ─────────────────────────────────────────────────────────────────
      Start writing your note…
    """

    content_changed = Signal(str, str)   # (title, body)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {_RIGHT_BG};")
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background: {_RIGHT_BG};")

        # ── Empty state (index 0) ──────────────────────────────────────────
        empty = QWidget()
        empty.setStyleSheet(f"background: {_RIGHT_BG};")
        el = QVBoxLayout(empty)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)

        el_t = QLabel("No page selected")
        el_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el_t.setStyleSheet(f"color: {_T_TER}; font-size: 11pt; background: transparent;")
        el.addWidget(el_t)

        el_h = QLabel("Select a page from the tree, or press + to create one")
        el_h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el_h.setWordWrap(True)
        el_h.setStyleSheet(f"color: {_T_DIM}; font-size: 8.5pt; background: transparent;")
        el.addWidget(el_h)
        self._stack.addWidget(empty)

        # ── Editor (index 1) ───────────────────────────────────────────────
        page = QWidget()
        page.setStyleSheet(f"background: {_RIGHT_BG};")
        pl = QVBoxLayout(page)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)

        # Title + last-edited bar
        tbar = QWidget()
        tbar.setFixedHeight(64)
        tbar.setStyleSheet(f"background: {_RIGHT_BG};")
        tbl = QHBoxLayout(tbar)
        tbl.setContentsMargins(40, 0, 40, 0)
        tbl.setSpacing(12)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Page title")
        tf = QFont()
        tf.setPointSize(20)
        tf.setWeight(QFont.Weight.Bold)
        self._title_edit.setFont(tf)
        self._title_edit.setStyleSheet(
            f"QLineEdit {{"
            f"  background: transparent; border: none; color: {_T_PRI};"
            f"  font-size: 20pt; font-weight: 700;"
            f"  selection-background-color: rgba(255,255,255,0.12);"
            f"}}"
        )
        self._title_edit.textChanged.connect(self._on_change)
        tbl.addWidget(self._title_edit, 1)

        self._ts_lbl = QLabel()
        self._ts_lbl.setStyleSheet(
            f"color: {_T_TER}; font-size: 7.5pt; font-family: '{_MONO}';"
            "letter-spacing: 0.3px; background: transparent;"
        )
        self._ts_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        tbl.addWidget(self._ts_lbl)

        pl.addWidget(tbar)
        pl.addWidget(_hdiv("rgba(255,255,255,0.10)"))

        # Body editor
        self._editor = QTextEdit()
        self._editor.setPlaceholderText("Start writing your note…")
        bf = QFont("Georgia", 10)
        bf.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self._editor.setFont(bf)

        fmt = QTextBlockFormat()
        fmt.setLineHeight(180, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        cur = self._editor.textCursor()
        cur.select(QTextCursor.SelectionType.Document)
        cur.setBlockFormat(fmt)
        self._editor.setTextCursor(cur)

        self._editor.setStyleSheet(
            f"QTextEdit {{"
            f"  background: transparent; color: {_T_PRI}; border: none;"
            f"  padding: 20px 40px 20px 40px;"
            f"  letter-spacing: 0.15px;"
            f"  selection-background-color: rgba(255,255,255,0.12);"
            f"  selection-color: {_T_PRI};"
            f"}}"
        )
        self._editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._editor.textChanged.connect(self._on_change)
        pl.addWidget(self._editor, 1)

        self._stack.addWidget(page)
        lay.addWidget(self._stack, 1)

    # ── Internal ──────────────────────────────────────────────────────────

    def _on_change(self) -> None:
        self.content_changed.emit(self._title_edit.text(), self._editor.toPlainText())

    def _fmt_timestamp(self, updated_at: str) -> str:
        if not updated_at:
            return ""
        try:
            dt = datetime.fromisoformat(updated_at)
            today = datetime.now().date()
            if dt.date() == today:
                return f"Last edited: Today, {dt.strftime('%I:%M %p').lstrip('0')}"
            return f"Last edited: {dt.strftime('%b %d, %I:%M %p').lstrip('0')}"
        except ValueError:
            return ""

    # ── Public API ────────────────────────────────────────────────────────

    def show_empty(self) -> None:
        self._stack.setCurrentIndex(0)

    def load_node(self, title: str, content: str, updated_at: str = "") -> None:
        self._stack.setCurrentIndex(1)

        self._title_edit.blockSignals(True)
        self._editor.blockSignals(True)

        self._title_edit.setText(title)
        self._editor.setPlainText(content)
        self._ts_lbl.setText(self._fmt_timestamp(updated_at))

        self._title_edit.blockSignals(False)
        self._editor.blockSignals(False)

        self._editor.setFocus()
        c = self._editor.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        self._editor.setTextCursor(c)

    def mark_saved(self, updated_at: str = "") -> None:
        if updated_at:
            self._ts_lbl.setText(self._fmt_timestamp(updated_at))

    def get_title(self) -> str:
        return self._title_edit.text().strip() or "Untitled"

    def get_content(self) -> str:
        return self._editor.toPlainText()


# ── NotesPage (top-level widget) ──────────────────────────────────────────────

class NotesPage(QWidget):
    def __init__(self, service: ProductivityService) -> None:
        super().__init__()
        self.service = service
        self.setStyleSheet(f"background: {_RIGHT_BG};")
        self._current_node_id: int | None = None

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(_AUTOSAVE_MS)
        self._save_timer.timeout.connect(self._do_save)

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._left = _LeftPanel(self.service)
        self._left.note_selected.connect(self._on_node_selected)
        self._left.sidebar_toggle_requested.connect(self._toggle_sidebar)
        self._left.delete_requested.connect(self._on_delete_requested)
        root.addWidget(self._left)

        self._divider = _vdiv("rgba(255,255,255,0.08)")
        root.addWidget(self._divider)

        self._editor = _EditorPanel()
        self._editor.content_changed.connect(self._on_content_changed)
        root.addWidget(self._editor, 1)

        # Undo Toast
        self._toast = _Toast(self)
        self._toast.undo_requested.connect(self._undo_delete)

        self._pending_delete_id: int | None = None
        self._pending_delete_timer = QTimer(self)
        self._pending_delete_timer.setSingleShot(True)
        self._pending_delete_timer.timeout.connect(self._commit_delete)

        # Floating toggle button for when sidebar is hidden
        self._floating_toggle = QPushButton(self)
        self._floating_toggle.setIcon(_svg_icon(_SVG_MENU, 14))
        self._floating_toggle.setIconSize(QSize(14, 14))
        self._floating_toggle.setFixedSize(26, 26)
        self._floating_toggle.setFlat(True)
        self._floating_toggle.setToolTip("Show sidebar")
        self._floating_toggle.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 5px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); }"
        )
        self._floating_toggle.clicked.connect(self._toggle_sidebar)
        self._floating_toggle.hide()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Position floating toggle at top left, matching the left panel's header padding
        self._floating_toggle.move(16, 14)
        self._toast.reposition()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._commit_delete()
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._do_save()

    def _on_node_selected(self, node_id: int) -> None:
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._do_save()

        if node_id == -1:
            self._current_node_id = None
            self._editor.show_empty()
            return

        self._current_node_id = node_id
        node = self.service.get_node(node_id)
        if node:
            self._editor.load_node(node.title, node.content, node.updated_at)

    def _on_content_changed(self, _t: str, _b: str) -> None:
        self._save_timer.start()

    def _do_save(self) -> None:
        if self._current_node_id is None:
            return
        self.service.update_node(
            self._current_node_id,
            self._editor.get_content(),
            self._editor.get_title(),
        )
        # Fetch updated timestamp
        node = self.service.get_node(self._current_node_id)
        ts = node.updated_at if node else ""
        self._editor.mark_saved(ts)
        self._left.populate(select_node_id=self._current_node_id)

    def refresh(self) -> None:
        self._left.populate(select_node_id=self._current_node_id)
        if self._current_node_id is None:
            self._editor.show_empty()

    def _on_delete_requested(self, node_id: int) -> None:
        # Commit any existing pending delete
        self._commit_delete()

        self._pending_delete_id = node_id
        self._left.hide_node(node_id)
        self._toast.show()
        self._toast.reposition()
        self._toast.raise_()
        self._pending_delete_timer.start(6000) # 6 seconds undo window

    def _undo_delete(self) -> None:
        if self._pending_delete_id is not None:
            self._pending_delete_timer.stop()
            self._left.unhide_node(self._pending_delete_id)
            self._pending_delete_id = None
            self._toast.hide()

    def _commit_delete(self) -> None:
        if self._pending_delete_id is not None:
            self.service.delete_node(self._pending_delete_id)
            self._pending_delete_id = None
            self._toast.hide()

    def _toggle_sidebar(self) -> None:
        """Collapse or expand the left panel + divider."""
        visible = self._left.isVisible()
        self._left.setVisible(not visible)
        self._divider.setVisible(not visible)
        self._floating_toggle.setVisible(visible)
