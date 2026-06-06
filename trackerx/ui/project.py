from __future__ import annotations

from PySide6.QtCore import Qt, QEvent, QSize
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont,
    QPixmap, QIcon, QFontMetrics,
)
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QFrame,
)

from ..core.models import Project, ProjectIdea
from ..core.services import ProductivityService
from .helper.icons import build_orbit_icon
from .helper.toolbar import ToolBar


# ── Strict B&W / Grey Palette ──────────────────────────────────────────────────
_BG          = "#111111"   # page background, dark theme canvas
_CARD_BG     = "#1c1c1e"   # card resting surface (matches recent task card)
_CARD_HOV    = "#242427"   # card hover surface (matches recent task card hover)
_SURFACE_IN  = "#1c1c1c"   # inset surface (inputs)
_BORDER      = "#1e1e1e"   # default border
_BORDER_MID  = "#2c2c2c"   # mid-weight border
_BORDER_HOV  = "#3d3d3d"   # hover border
_DIVIDER     = "#1a1a1a"   # hairline divider
_T_PRI       = "#efefef"   # primary text
_T_SEC       = "#888888"   # secondary text
_T_TER       = "#555555"   # tertiary / muted text
_T_DIM       = "#333333"   # very dim / decorative
_BADGE_BG    = "#181818"   # idea-count badge
_BADGE_FG    = "#4a4a4a"   # idea-count text
_DEL_HOV_BG  = "#1e1e1e"   # delete button hover

_CARD_W      = 250
_CARD_GAP    = 18
_CARD_H      = 264
_GRID_COLS   = 4

_MONO_FONT   = "Courier New"   # monospace accent for badge / stats


# ── Icon helpers ───────────────────────────────────────────────────────────────

def _cross_icon(color: str = _T_TER) -> QIcon:
    """Crisp ✕ for delete buttons."""
    pix = QPixmap(14, 14)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(3, 3, 11, 11)
    p.drawLine(11, 3, 3, 11)
    p.end()
    return QIcon(pix)


def _make_avatar(letter: str, size: int = 28) -> QPixmap:
    """Circular monogram avatar — pure greyscale."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Outer ring
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor("#3a3a3a"), 1.0))
    p.drawEllipse(0, 0, size - 1, size - 1)

    # Fill
    p.setBrush(QColor("#232325"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(1, 1, size - 2, size - 2)

    # Letter
    font = QFont("Segoe UI", int(size * 0.36), QFont.Weight.DemiBold)
    p.setFont(font)
    p.setPen(QColor("#d4d4d4"))
    p.drawText(0, 0, size, size, Qt.AlignmentFlag.AlignCenter, letter.upper()[:1])
    p.end()
    return pix


# ── Page header strip ──────────────────────────────────────────────────────────

class _HeaderStrip(QWidget):
    """
    Live project/idea count stat and search field only.
    No title heading, no divider. Strictly B&W/grey.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")
        self._build()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(36, 22, 36, 10)
        lay.setSpacing(0)

        # ── Left: stats only (no title heading) ───────────────────────────
        self.stats_lbl = QLabel()
        self.stats_lbl.setStyleSheet(
            f"color: {_T_PRI};"
            f"font-size: 10pt;"
            f"background: transparent;"
            f"letter-spacing: 0.1px;"
        )
        lay.addWidget(self.stats_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
        lay.addStretch(1)

        # ── Right: search ──────────────────────────────────────────────────
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search…")
        self.search.setFixedWidth(200)
        self.search.setFixedHeight(32)
        self.search.setStyleSheet(
            f"QLineEdit {{"
            f"  background: {_SURFACE_IN};"
            f"  color: {_T_PRI};"
            f"  border: 1px solid {_BORDER_MID};"
            f"  border-radius: 6px;"
            f"  padding: 0 10px;"
            f"  font-size: 8.5pt;"
            f"}}"
            f"QLineEdit:focus {{"
            f"  border-color: {_BORDER_HOV};"
            f"  background: #1f1f1f;"
            f"}}"
            f"QLineEdit::placeholder {{"
            f"  color: {_T_DIM};"
            f"}}"
        )
        lay.addWidget(self.search, alignment=Qt.AlignmentFlag.AlignVCenter)

    def update_stats(self, n_projects: int, n_ideas: int) -> None:
        p = f"{n_projects} project{'s' if n_projects != 1 else ''}"
        i = f"{n_ideas} idea{'s' if n_ideas != 1 else ''}"
        self.stats_lbl.setText(f"{p}  ·  {i}".upper())


# ── Thin horizontal rule ──────────────────────────────────────────────────────

def _make_divider() -> QFrame:
    d = QFrame()
    d.setFrameShape(QFrame.Shape.HLine)
    d.setFixedHeight(1)
    d.setStyleSheet(f"background: {_DIVIDER}; border: none;")
    return d


# ── Single idea row ────────────────────────────────────────────────────────────

class _IdeaRow(QWidget):
    """
    One idea inside a card.  Dim at rest → brighter + delete on hover.
    """

    def __init__(self, idea: ProjectIdea, parent_card: "_ProjectCard | None" = None) -> None:
        super().__init__(parent_card)
        self.idea = idea
        self.parent_card = parent_card
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setStyleSheet("background: transparent;")
        self._build()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 1, 0, 1)
        lay.setSpacing(7)

        # Bullet
        dot = QLabel("·")
        dot.setFixedWidth(8)
        dot.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        dot.setStyleSheet(
            f"color: {_T_DIM}; background: transparent;"
            f"font-size: 11pt; padding-top: 2px;"
        )
        lay.addWidget(dot, alignment=Qt.AlignmentFlag.AlignTop)

        self.lbl = QLabel(self.idea.title)
        self.lbl.setWordWrap(True)
        self._dim_ss = (
            f"color: {_T_SEC}; font-size: 9pt;"
            f"background: transparent; letter-spacing: 0.1px; line-height: 1.4;"
        )
        self._hov_ss = (
            f"color: {_T_PRI}; font-size: 9pt;"
            f"background: transparent; letter-spacing: 0.1px; line-height: 1.4;"
        )
        self.lbl.setStyleSheet(self._dim_ss)
        lay.addWidget(self.lbl, 1)

        self.del_btn = QPushButton()
        self.del_btn.setIcon(_cross_icon())
        self.del_btn.setIconSize(QSize(10, 10))
        self.del_btn.setFixedSize(18, 18)
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; }}"
            f"QPushButton:hover {{ background: {_SURFACE_IN}; border-radius: 4px; }}"
        )
        self.del_btn.setVisible(False)
        self.del_btn.clicked.connect(self._on_delete)
        lay.addWidget(self.del_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

    def enterEvent(self, _) -> None:
        self.del_btn.setVisible(True)
        self.lbl.setStyleSheet(self._hov_ss)

    def leaveEvent(self, _) -> None:
        self.del_btn.setVisible(False)
        self.lbl.setStyleSheet(self._dim_ss)

    def _on_delete(self) -> None:
        if self.parent_card:
            self.parent_card.delete_idea(self.idea.id)


# ── Project card ───────────────────────────────────────────────────────────────

class _ProjectCard(QWidget):
    """
    Project card — fixed width, adapts visually to its idea count.

    Layout (top → bottom):
      header row  (avatar · title · badge · ⋯)
      description  [optional]
      ── divider ──
      idea list    (flexible height, fills available space via stretch=1)
      idea input   (hidden until activated)
      + capture    button
    """

    _NORMAL_SS = (
        "QWidget#ProjCard {"
        f"  background: {_CARD_BG};"
        f"  border: 1px solid {_BORDER};"
        "  border-radius: 10px;"
        "}"
    )
    _HOVER_SS = (
        "QWidget#ProjCard {"
        f"  background: {_CARD_HOV};"
        f"  border: 1px solid {_BORDER_MID};"
        "  border-radius: 10px;"
        "}"
    )

    def __init__(self, project: Project, parent_page: "ProjectPage | None" = None) -> None:
        super().__init__(parent_page)
        self.project = project
        self.parent_page = parent_page
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._build()

    # ── Construction ──────────────────────────────────────────────────────

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Card shell ─────────────────────────────────────────────────────
        self.card = QWidget()
        self.card.setObjectName("ProjCard")
        self.card.setFixedSize(_CARD_W, _CARD_H)
        self.card.setStyleSheet(self._NORMAL_SS)
        self.card.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.card.installEventFilter(self)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.card.setGraphicsEffect(shadow)

        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(14, 12, 14, 10)
        cl.setSpacing(0)

        # ── Header row ─────────────────────────────────────────────────────
        hrow = QHBoxLayout()
        hrow.setContentsMargins(0, 0, 0, 0)
        hrow.setSpacing(7)

        av = QLabel()
        av.setPixmap(_make_avatar(self.project.title, 24))
        av.setFixedSize(24, 24)
        hrow.addWidget(av)

        title_lbl = QLabel(self.project.title)
        title_lbl.setStyleSheet(
            f"color: {_T_PRI};"
            f"font-size: 9.5pt; font-weight: 600;"
            f"background: transparent; letter-spacing: 0.05px;"
        )
        hrow.addWidget(title_lbl, 1)

        # Idea-count badge (monospace, understated)
        n = len(self.project.ideas or [])
        if n:
            badge = QLabel(str(n))
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(18, 14)
            badge.setStyleSheet(
                f"background: {_BADGE_BG};"
                f"color: {_T_PRI};"
                f"font-size: 7pt; font-weight: 600;"
                f"border: 1px solid {_BORDER_MID};"
                f"border-radius: 3px;"
            )
            hrow.addWidget(badge)

        # ⋯ edit button
        edit_btn = QPushButton("···")
        edit_btn.setFixedSize(22, 20)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setToolTip("Edit project")
        edit_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent; border: none;"
            f"  color: {_T_SEC}; padding: 0; font-size: 9pt; letter-spacing: 1px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  color: {_T_PRI};"
            f"  background: rgba(255,255,255,0.08);"
            f"  border-radius: 5px;"
            f"}}"
            f"QPushButton:pressed {{"
            f"  color: {_T_PRI};"
            f"  background: rgba(255,255,255,0.14);"
            f"}}"
        )
        edit_btn.clicked.connect(self._edit_project)
        hrow.addWidget(edit_btn)
        cl.addLayout(hrow)

        # ── Description ────────────────────────────────────────────────────
        if self.project.description:
            desc_lbl = QLabel(self.project.description)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(
                f"color: {_T_SEC};"
                f"font-size: 8pt;"
                f"background: transparent;"
                f"margin-top: 6px;"
                f"letter-spacing: 0.15px;"
                f"line-height: 1.5;"
            )
            cl.addWidget(desc_lbl)

        # ── Divider ─────────────────────────────────────────────────────────
        div = _make_divider()
        div.setContentsMargins(0, 0, 0, 0)
        div.setStyleSheet(
            f"background: {_DIVIDER}; border: none;"
            f"margin-top: 14px; margin-bottom: 6px;"
        )
        cl.addWidget(div)

        # ── Ideas scroll ─────────────────────────────────────────────────
        self.ideas_box = QWidget()
        self.ideas_box.setStyleSheet("background: transparent;")
        self.ideas_lay = QVBoxLayout(self.ideas_box)
        self.ideas_lay.setContentsMargins(0, 0, 0, 0)
        self.ideas_lay.setSpacing(3)

        for idea in (self.project.ideas or []):
            self.ideas_lay.addWidget(_IdeaRow(idea, parent_card=self))
        self.ideas_lay.addStretch(1)

        self.ideas_scroll = QScrollArea()
        self.ideas_scroll.setWidgetResizable(True)
        self.ideas_scroll.setMinimumHeight(60)
        self.ideas_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.ideas_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.ideas_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.ideas_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical {"
            f"  width: 3px; background: transparent; margin: 0;"
            "}"
            "QScrollBar::handle:vertical {"
            f"  background: {_BORDER_MID}; border-radius: 1px; min-height: 20px;"
            "}"
            "QScrollBar::add-line, QScrollBar::sub-line,"
            "QScrollBar::add-page, QScrollBar::sub-page { height: 0; }"
        )
        self.ideas_scroll.setWidget(self.ideas_box)
        cl.addWidget(self.ideas_scroll, 1)

        # ── Idea capture input (hidden until activated) ─────────────────────
        self.idea_input = QLineEdit()
        self.idea_input.setPlaceholderText("New idea…   ↵ save   Esc cancel")
        self.idea_input.setFixedHeight(22)
        self.idea_input.setStyleSheet(
            f"QLineEdit {{"
            f"  background: {_SURFACE_IN};"
            f"  color: {_T_PRI};"
            f"  border: 1px solid {_BORDER_MID};"
            f"  border-radius: 6px;"
            f"  padding: 0 9px;"
            f"  font-size: 8.5pt;"
            f"}}"
            f"QLineEdit:focus {{"
            f"  border-color: {_BORDER_HOV};"
            f"}}"
        )
        self.idea_input.returnPressed.connect(self._commit_idea)
        self.idea_input.installEventFilter(self)
        self.idea_input.setVisible(False)
        cl.addWidget(self.idea_input)

        # ── Spacer between input area and + button ─────────────────────────
        cl.addSpacing(4)

        # ── "+ Capture idea" button ─────────────────────────────────────────
        self.add_btn = QPushButton("＋  Capture idea")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setFixedHeight(20)
        self.add_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent; border: none;"
            f"  color: {_T_SEC}; font-size: 9pt;"
            f"  padding: 0; text-align: left;"
            f"}}"
            f"QPushButton:hover {{ color: {_T_PRI}; }}"
        )
        self.add_btn.clicked.connect(self._show_idea_input)
        cl.addWidget(self.add_btn)

        outer.addWidget(self.card)

    # ── Idea input helpers ─────────────────────────────────────────────────

    def _show_idea_input(self) -> None:
        self.add_btn.setVisible(False)
        self.idea_input.setVisible(True)
        self.idea_input.clear()
        self.idea_input.setFocus()

    def _hide_idea_input(self) -> None:
        self.idea_input.setVisible(False)
        self.idea_input.clear()
        self.add_btn.setVisible(True)

    def _commit_idea(self) -> None:
        text = self.idea_input.text().strip()
        if text and self.parent_page:
            self.parent_page.add_idea(self.project.id, text)
        else:
            self._hide_idea_input()

    # ── Forwarded actions ──────────────────────────────────────────────────

    def delete_idea(self, idea_id: int | None) -> None:
        if idea_id is not None and self.parent_page:
            self.parent_page.delete_idea(idea_id)

    def _edit_project(self) -> None:
        if self.parent_page:
            self.parent_page.edit_project(self.project.id)

    # ── Event filter ──────────────────────────────────────────────────────

    def eventFilter(self, obj, event) -> bool:
        if obj is self.card:
            t = event.type()
            if t == QEvent.Type.Enter:
                self.card.setStyleSheet(self._HOVER_SS)
            elif t == QEvent.Type.Leave:
                self.card.setStyleSheet(self._NORMAL_SS)
        elif obj is self.idea_input:
            if (
                event.type() == QEvent.Type.KeyPress
                and event.key() == Qt.Key.Key_Escape
            ):
                self._hide_idea_input()
                return True
        return super().eventFilter(obj, event)


# ── Project form dialog ────────────────────────────────────────────────────────

class ProjectFormDialog(QDialog):
    """Create or edit a project.  Strict B&W/grey aesthetic."""

    def __init__(self, parent=None, project: Project | None = None) -> None:
        super().__init__(parent)
        self.setWindowIcon(build_orbit_icon(16))
        self.setWindowTitle("Edit Project" if project else "New Project")
        self.resize(440, 240)
        self.original = project
        self.delete_requested = False
        self._apply_styles()
        self._build()
        if project:
            self.title_edit.setText(project.title)
            self.desc_edit.setPlainText(project.description or "")

    def _apply_styles(self) -> None:
        self.setStyleSheet(f"""
            QDialog {{
                background: #0e0e0e;
                color: {_T_PRI};
            }}
            QLabel {{
                color: {_T_SEC};
                font-size: 8.5pt;
                background: transparent;
            }}
            QLineEdit, QTextEdit {{
                background: {_SURFACE_IN};
                color: {_T_PRI};
                border: 1px solid {_BORDER_MID};
                border-radius: 7px;
                padding: 6px 10px;
                font-size: 9.5pt;
                selection-background-color: #3a3a3a;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {_BORDER_HOV};
            }}
        """)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(18)

        # Heading
        heading = QLabel("Edit project" if self.original else "New project")
        heading.setStyleSheet(
            f"color: {_T_PRI}; font-size: 13pt; font-weight: 700;"
            f"background: transparent; letter-spacing: -0.3px;"
        )
        lay.addWidget(heading)

        # Form
        form = QFormLayout()
        form.setSpacing(10)
        form.setHorizontalSpacing(18)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Project name")
        self.title_edit.setFixedHeight(32)
        self.title_edit.returnPressed.connect(self.accept)
        form.addRow(QLabel("Name"), self.title_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Short description  (optional)")
        self.desc_edit.setFixedHeight(66)
        form.addRow(QLabel("About"), self.desc_edit)
        lay.addLayout(form)

        # Action row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        if self.original:
            del_btn = QPushButton("Delete")
            del_btn.setFixedHeight(30)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet(
                f"QPushButton {{"
                f"  background: transparent;"
                f"  border: 1px solid {_BORDER_MID};"
                f"  color: {_T_DIM};"
                f"  border-radius: 7px;"
                f"  padding: 0 16px; font-size: 8.5pt;"
                f"}}"
                f"QPushButton:hover {{"
                f"  border-color: #4a2020;"
                f"  color: #8a4040;"
                f"}}"
            )
            del_btn.clicked.connect(self._on_delete)
            btn_row.addWidget(del_btn)

        btn_row.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(30)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent;"
            f"  border: 1px solid {_BORDER_MID};"
            f"  color: {_T_SEC};"
            f"  border-radius: 7px;"
            f"  padding: 0 18px; font-size: 8.5pt;"
            f"}}"
            f"QPushButton:hover {{"
            f"  border-color: {_BORDER_HOV};"
            f"  color: {_T_PRI};"
            f"}}"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(30)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(
            "QPushButton {"
            "  background: #e8e8e8; color: #0a0a0a;"
            "  border: none; border-radius: 7px;"
            "  padding: 0 24px; font-weight: 700; font-size: 8.5pt;"
            "}"
            "QPushButton:hover { background: #ffffff; }"
            "QPushButton:pressed { background: #d0d0d0; }"
        )
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

    def _on_delete(self) -> None:
        self.delete_requested = True
        self.accept()

    def get_data(self) -> tuple[str, str]:
        return (
            self.title_edit.text().strip() or "Untitled",
            self.desc_edit.toPlainText().strip(),
        )


# ── Main page ──────────────────────────────────────────────────────────────────

class ProjectPage(QWidget):
    """
    Scrollable grid of project cards (centred, _GRID_COLS per row).

    Grid rows use symmetric leading/trailing stretches so cards are
    horizontally centred regardless of how many are in the last row.
    """

    def __init__(self, service: ProductivityService) -> None:
        super().__init__()
        self.service = service
        self._all_projects: list[Project] = []
        self.setStyleSheet(f"background: {_BG};")
        self._build_ui()
        self.refresh()

    # ── UI skeleton ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Shared toolbar
        self.toolbar = ToolBar(self)
        self.toolbar.add_button.clicked.connect(self.add_project)
        root.addWidget(self.toolbar)

        # Header (stats + search only — no title, no divider)
        self._header = _HeaderStrip(self)
        self._header.search.textChanged.connect(self._apply_filter)
        root.addWidget(self._header)

        # Scrollable grid
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: {_BG}; border: none; }}"
            "QScrollBar:vertical { width: 5px; background: transparent; margin: 0; }"
            "QScrollBar::handle:vertical {"
            f"  background: {_BORDER_MID}; border-radius: 2px; min-height: 24px;"
            "}"
            "QScrollBar::add-line, QScrollBar::sub-line { height: 0; }"
        )

        self._body = QWidget()
        self._body.setStyleSheet(f"background: {_BG};")
        self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(36, 26, 36, 36)
        self._body_lay.setSpacing(0)

        self._scroll.setWidget(self._body)
        root.addWidget(self._scroll, 1)

    # ── Refresh / render ──────────────────────────────────────────────────

    def refresh(self) -> None:
        self._all_projects = self.service.list_projects()
        n_ideas = sum(len(p.ideas or []) for p in self._all_projects)
        self._header.update_stats(len(self._all_projects), n_ideas)
        self._apply_filter(self._header.search.text())

    def _apply_filter(self, query: str) -> None:
        q = query.strip().lower()
        if q:
            visible = [
                p for p in self._all_projects
                if q in p.title.lower() or q in (p.description or "").lower()
            ]
        else:
            visible = self._all_projects
        self._render(visible, is_filtered=bool(q))

    def _render(self, projects: list[Project], is_filtered: bool = False) -> None:
        # Clear
        while self._body_lay.count():
            item = self._body_lay.takeAt(0)
            if w := item.widget():
                w.deleteLater()

        if not projects:
            self._render_empty(filtered=is_filtered)
            return

        for row_start in range(0, len(projects), _GRID_COLS):
            chunk = projects[row_start: row_start + _GRID_COLS]

            row_w = QWidget()
            row_w.setStyleSheet("background: transparent;")
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(_CARD_GAP)
            row_lay.setAlignment(Qt.AlignmentFlag.AlignTop)

            # Leading stretch → centres the card cluster horizontally
            row_lay.addStretch(1)

            for proj in chunk:
                row_lay.addWidget(
                    _ProjectCard(proj, parent_page=self),
                    alignment=Qt.AlignmentFlag.AlignTop,
                )

            # Trailing stretch → mirrors the leading stretch
            row_lay.addStretch(1)

            self._body_lay.addWidget(row_w)
            self._body_lay.addSpacing(_CARD_GAP)

        self._body_lay.addStretch(1)

    def _render_empty(self, filtered: bool = False) -> None:
        self._body_lay.addStretch(1)

        if filtered:
            sym = QLabel("○")
            sym.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sym.setStyleSheet(
                f"color: {_T_DIM}; font-size: 20pt; background: transparent;"
            )
            self._body_lay.addWidget(sym, alignment=Qt.AlignmentFlag.AlignCenter)
            self._body_lay.addSpacing(10)

            msg = QLabel("No projects match your search.")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet(
                f"color: {_T_TER}; font-size: 9.5pt; background: transparent;"
            )
            self._body_lay.addWidget(msg, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            sym = QLabel("□")
            sym.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sym.setStyleSheet(
                f"color: {_T_DIM}; font-size: 26pt; background: transparent;"
            )
            self._body_lay.addWidget(sym, alignment=Qt.AlignmentFlag.AlignCenter)
            self._body_lay.addSpacing(12)

            msg = QLabel("No projects yet.\nPress  +  in the toolbar to create your first project.")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet(
                f"color: {_T_TER}; font-size: 9.5pt; background: transparent;"
                f"line-height: 1.8;"
            )
            self._body_lay.addWidget(msg, alignment=Qt.AlignmentFlag.AlignCenter)

        self._body_lay.addStretch(1)

    # ── Project CRUD ──────────────────────────────────────────────────────

    def add_project(self) -> None:
        dlg = ProjectFormDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            title, desc = dlg.get_data()
            self.service.create_project(
                Project(id=None, title=title, description=desc)
            )
            self.refresh()

    def edit_project(self, project_id: int | None) -> None:
        if project_id is None:
            return
        proj = self.service.get_project(project_id)
        if not proj:
            return
        dlg = ProjectFormDialog(self, proj)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg.delete_requested:
                self.service.delete_project(project_id)
            else:
                title, desc = dlg.get_data()
                proj.title = title
                proj.description = desc
                self.service.update_project(project_id, proj)
            self.refresh()

    # ── Idea CRUD ─────────────────────────────────────────────────────────

    def add_idea(self, project_id: int | None, text: str) -> None:
        if project_id is None:
            return
        self.service.add_project_idea(
            project_id,
            ProjectIdea(id=None, project_id=project_id, title=text),
        )
        self.refresh()

    def delete_idea(self, idea_id: int) -> None:
        self.service.delete_project_idea(idea_id)
        self.refresh()