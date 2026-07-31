from __future__ import annotations

from PySide6.QtCore import Qt, QEvent, QSize, Signal, QTimer
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
    QGridLayout,
    QToolButton,
)

from core.models import Project, ProjectIdea
from core.services import ProductivityService
from .helper.icons import build_orbit_icon
from .helper.toolbar import ToolBar
from .helper.drawer import SlideOutDrawer
from .helper.flow_layout import FlowLayout


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


class _ElidedLabel(QLabel):
    """A label that gracefully elides its text with an ellipsis if it exceeds the width."""
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(1)

    def setText(self, text: str) -> None:
        self._full_text = text
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width())
        
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)
        painter.end()

    def minimumSizeHint(self) -> QSize:
        return QSize(1, super().minimumSizeHint().height())



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

        title_lbl = _ElidedLabel(self.project.title)
        title_lbl.setToolTip(self.project.title)
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
                f"background: transparent;"
                f"color: {_T_PRI};"
                f"font-size: 7pt; font-weight: 600;"
                f"border: 1px solid {_BORDER_MID};"
                f"border-radius: 3px;"
            )
            hrow.addWidget(badge)


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
            
        # ── Idea capture input (inline, hidden until activated) ───────────
        self.idea_input = QLineEdit()
        self.idea_input.setPlaceholderText("New idea…")
        self.idea_input.setFixedHeight(22)
        self.idea_input.setStyleSheet(
            f"QLineEdit {{"
            f"  background: transparent;"
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
        self.ideas_lay.addWidget(self.idea_input)

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
        self.idea_input.setVisible(True)
        self.idea_input.clear()
        self.idea_input.setFocus()

    def _hide_idea_input(self) -> None:
        self.idea_input.setVisible(False)
        self.idea_input.clear()

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
            elif t == QEvent.Type.MouseButtonDblClick:
                self._edit_project()
        elif obj is self.idea_input:
            if (
                event.type() == QEvent.Type.KeyPress
                and event.key() == Qt.Key.Key_Escape
            ):
                self._hide_idea_input()
                return True
            elif event.type() == QEvent.Type.FocusOut:
                self._commit_idea()
        return super().eventFilter(obj, event)


# ── Project form dialog ────────────────────────────────────────────────────────

class ProjectFormWidget(QWidget):
    """Create or edit a project.  Strict B&W/grey aesthetic."""
    saved = Signal(str, str)
    deleted = Signal()
    cancelled = Signal()

    def __init__(self, parent=None, project: Project | None = None) -> None:
        super().__init__(parent)
        self.original = project
        self._apply_styles()
        self._build()
        if project:
            self.title_edit.setText(project.title)
            self.desc_edit.setPlainText(project.description or "")

    def _apply_styles(self) -> None:
        self.setStyleSheet(f"""
            QWidget#FormCard {{
                background: transparent;
            }}
            QLabel {{
                background: transparent;
            }}
        """)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        form_card = QWidget()
        form_card.setObjectName("FormCard")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(24)

        input_style = """
            QLineEdit, QTextEdit {
                background-color: #1a1a1c;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 10px;
                color: #ffffff;
                font-size: 10pt;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """

        label_style = "color: #e8e8ed; font-size: 9.5pt; font-weight: 500;"

        # ── Title ──
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)
        lbl_title = QLabel("Name")
        lbl_title.setStyleSheet(label_style)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Project name")
        self.title_edit.setStyleSheet(input_style)
        title_layout.addWidget(lbl_title)
        title_layout.addWidget(self.title_edit)

        # ── Description ──
        desc_container = QWidget()
        desc_layout = QVBoxLayout(desc_container)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        desc_layout.setSpacing(8)
        lbl_desc = QLabel("About")
        lbl_desc.setStyleSheet(label_style)
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Short description (optional)")
        self.desc_edit.setMaximumHeight(120)
        self.desc_edit.setStyleSheet(input_style)
        desc_layout.addWidget(lbl_desc)
        desc_layout.addWidget(self.desc_edit)

        form_layout.addWidget(title_container)
        form_layout.addWidget(desc_container)
        form_layout.addStretch(1)

        scroll.setWidget(form_card)
        lay.addWidget(scroll)

        # ── Action Buttons ──
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(12)

        save_btn = QPushButton("Save Project" if self.original else "Create Project")
        save_btn.setFixedHeight(44)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2c;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: 500;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #353538;
            }
        """)
        save_btn.clicked.connect(lambda: self.saved.emit(*self.get_data()))
        self.title_edit.returnPressed.connect(save_btn.click)
        btn_row.addWidget(save_btn, 1)

        if self.original:
            del_btn = QPushButton("Delete")
            del_btn.setFixedHeight(44)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a1a1c;
                    color: #ff6b6b;
                    border: none;
                    border-radius: 6px;
                    font-weight: 500;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #4a2a2c;
                }
            """)
            del_btn.clicked.connect(self._on_delete)
            btn_row.addWidget(del_btn)

        lay.addLayout(btn_row)

    def _on_delete(self) -> None:
        self.deleted.emit()

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
        self.drawer = SlideOutDrawer(width=380, parent=self)
        self._build_ui_layout()
        self.refresh()

    # ── UI skeleton ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        pass # Called just to prep before drawer init if needed

    def _build_ui_layout(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Toolbar is now inside body_layout so it slides with the content

        # Horizontal layout for body + drawer
        h_body_container = QWidget()
        h_body_layout = QHBoxLayout(h_body_container)
        h_body_layout.setContentsMargins(0, 0, 0, 0)
        h_body_layout.setSpacing(0)

        # Body container
        self.body_widget = QWidget()
        self.body_widget.installEventFilter(self)
        body_layout = QVBoxLayout(self.body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Shared toolbar
        self.toolbar = ToolBar(self)
        self.toolbar.add_button.clicked.connect(self.add_project)
        body_layout.addWidget(self.toolbar)

        # Header (stats + search only — no title, no divider)
        self._header = _HeaderStrip(self)
        self._header.search.textChanged.connect(self._apply_filter)
        body_layout.addWidget(self._header)

        # Scrollable grid
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
        body_layout.addWidget(self._scroll, 1)

        h_body_layout.addWidget(self.body_widget, stretch=1)
        h_body_layout.addWidget(self.drawer)
        
        root.addWidget(h_body_container, stretch=1)

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

        # Create a container for the flow layout
        flow_container = QWidget()
        flow_container.setStyleSheet("background: transparent;")
        
        # We configure the flow layout with no external margins, and spacing defined by _CARD_GAP
        flow_lay = FlowLayout(flow_container, margin=0, spacing=_CARD_GAP)
        
        for proj in projects:
            card = _ProjectCard(proj, parent_page=self)
            flow_lay.addWidget(card)
            
        self._body_lay.addWidget(flow_container)
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
        form = ProjectFormWidget(self)
        self.drawer.set_title("New Project")
        self.drawer.set_content(form)
        form.cancelled.connect(self.drawer.close_drawer)
        form.saved.connect(self._on_project_added)
        self.drawer.open_drawer()

    def _on_project_added(self, title: str, desc: str) -> None:
        self.drawer.close_drawer()
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
        
        form = ProjectFormWidget(self, proj)
        self.drawer.set_title("Edit Project")
        self.drawer.set_content(form)
        
        form.cancelled.connect(self.drawer.close_drawer)
        form.deleted.connect(lambda: self._on_project_deleted(project_id))
        form.saved.connect(lambda title, desc: self._on_project_edited(project_id, proj, title, desc))
        
        self.drawer.open_drawer()

    def _on_project_deleted(self, project_id: int) -> None:
        self.drawer.close_drawer()
        self.service.delete_project(project_id)
        self.refresh()

    def _on_project_edited(self, project_id: int, proj: Project, title: str, desc: str) -> None:
        self.drawer.close_drawer()
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
