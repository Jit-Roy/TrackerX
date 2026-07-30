from __future__ import annotations

from datetime import date, timedelta
from calendar import monthrange

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QButtonGroup,
)

from core.models import Habit


class _SegmentedToggle(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            _SegmentedToggle {
                background: #111113;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
        """)
        
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)
        
        self.btn_month = QPushButton("Month")
        self.btn_year = QPushButton("Year")
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.btn_month, 0)
        self.btn_group.addButton(self.btn_year, 1)
        
        base_style = """
            QPushButton {
                background: transparent;
                color: #636366;
                border: none;
                border-radius: 4px;
                font-size: 9pt;
                font-weight: 500;
            }
            QPushButton:checked {
                background: #232325;
                color: #e8e8ed;
            }
        """
        self.btn_month.setStyleSheet(base_style)
        self.btn_year.setStyleSheet(base_style)
        self.btn_month.setCheckable(True)
        self.btn_year.setCheckable(True)
        self.btn_month.setChecked(True)
        self.btn_month.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_year.setCursor(Qt.CursorShape.PointingHandCursor)
        
        lay.addWidget(self.btn_month)
        lay.addWidget(self.btn_year)


class _MonthCalendarGraph(QWidget):
    def __init__(self, target_date: date, created_date: date, completions: set[date], parent=None):
        super().__init__(parent)
        self.target_date = target_date
        self.created_date = created_date
        self.completions = completions
        
        self.cell_w = 36
        self.cell_h = 28
        self.gap = 4
        
        # 7 cols, 6 rows + header
        width = 7 * self.cell_w + 6 * self.gap
        height = 6 * self.cell_h + 5 * self.gap + 20
        self.setFixedSize(width, height)
        
        _, num_days = monthrange(target_date.year, target_date.month)
        first_day = date(target_date.year, target_date.month, 1)
        start_weekday = first_day.weekday()
        
        self.days_in_grid = []
        for i in range(42):
            if i < start_weekday or i >= start_weekday + num_days:
                self.days_in_grid.append(None)
            else:
                self.days_in_grid.append(first_day + timedelta(days=i - start_weekday))

    def paintEvent(self, e):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw day headers
            headers = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
            p.setPen(QColor("#636366"))
            
            for i, h in enumerate(headers):
                x = i * (self.cell_w + self.gap)
                p.drawText(QRect(x, 0, self.cell_w, 20), Qt.AlignmentFlag.AlignCenter, h)
                
            today = date.today()
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            
            for i, d in enumerate(self.days_in_grid):
                if d is None:
                    continue
                    
                col = i % 7
                row = i // 7
                x = col * (self.cell_w + self.gap)
                y = 20 + row * (self.cell_h + self.gap)
                r = QRect(x, y, self.cell_w, self.cell_h)
                
                is_completed = d in self.completions
                is_future = d > today
                is_before_created = d < self.created_date
                
                if is_completed:
                    bg = QColor("#e8e8ed")
                    fg = QColor("#111113")
                elif is_future:
                    bg = QColor(0,0,0,0)
                    fg = QColor("#555555")
                else:
                    # Missed
                    bg = QColor("#1a1a1c")
                    fg = QColor("#888888")
                    
                p.setBrush(bg)
                if not is_future and not is_completed:
                    p.setPen(QPen(QColor(255,255,255, 8), 1))
                else:
                    p.setPen(Qt.PenStyle.NoPen)
                    
                p.drawRoundedRect(r, 6, 6)
                
                p.setPen(fg)
                p.drawText(r, Qt.AlignmentFlag.AlignCenter, str(d.day))
                
        finally:
            p.end()


class _YearCalendarGraph(QWidget):
    def __init__(self, target_date: date, created_date: date, completions: set[date], parent=None):
        super().__init__(parent)
        self.target_date = target_date
        self.created_date = created_date
        self.completions = completions
        
        self.month_w = 64
        self.month_h = 60
        self.gap_x = 12
        self.gap_y = 16
        
        width = 4 * self.month_w + 3 * self.gap_x
        height = 3 * self.month_h + 2 * self.gap_y
        self.setFixedSize(width, height)

    def paintEvent(self, e):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            for m in range(1, 13):
                col = (m - 1) % 4
                row = (m - 1) // 4
                
                x = col * (self.month_w + self.gap_x)
                y = row * (self.month_h + self.gap_y)
                
                self._draw_month_block(p, x, y, m)
                
        finally:
            p.end()
        
    def _draw_month_block(self, p, x, y, month):
        year = self.target_date.year
        _, num_days = monthrange(year, month)
        first_day = date(year, month, 1)
        
        completed_days = sum(1 for i in range(num_days) if date(year, month, i+1) in self.completions)
        valid_days = 0
        today = date.today()
        for i in range(num_days):
            d = date(year, month, i+1)
            if self.created_date <= d <= today:
                valid_days += 1
                
        pct = int(completed_days / valid_days * 100) if valid_days > 0 else 0
        
        # header
        month_name = first_day.strftime("%b")
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        p.setPen(QColor("#e8e8ed"))
        p.drawText(QRect(x, y, 32, 15), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, month_name)
        
        p.setFont(QFont("Segoe UI", 7))
        p.setPen(QColor("#636366"))
        p.drawText(QRect(x+32, y, 32, 15), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{pct}%")
        
        # dot grid - draw sequentially to save space (max 5 rows)
        dot_r = 6
        dot_gap = 2
        
        # optional: border for current month
        if year == today.year and month == today.month:
            br = QRect(x-4, y+16, 7 * (dot_r + dot_gap) + 8 - dot_gap, 5 * (dot_r + dot_gap) + 8 - dot_gap)
            p.setPen(QPen(QColor("#444444"), 1))
            p.setBrush(Qt.GlobalColor.transparent)
            p.drawRoundedRect(br, 4, 4)
        
        for i in range(num_days):
            dot_col = i % 7
            dot_row = i // 7
            
            dx = x + dot_col * (dot_r + dot_gap)
            dy = y + 20 + dot_row * (dot_r + dot_gap)
            
            d = date(year, month, i+1)
            is_completed = d in self.completions
            is_future = d > today
            is_before_created = d < self.created_date
            
            if is_completed:
                p.setBrush(QColor("#e8e8ed"))
            elif is_future:
                p.setBrush(QColor(255,255,255,8))
            else:
                p.setBrush(QColor("#323234"))
                
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(dx, dy, dot_r, dot_r)


class HabitProgressSection(QWidget):
    def __init__(self, habit: Habit, completions: set[date], parent=None):
        super().__init__(parent)
        self.habit = habit
        self.completions = completions
        self.created_date = habit.created_date or date.today()
        
        self.current_month_date = date.today().replace(day=1)
        self.current_year_date = date.today().replace(month=1, day=1)
        
        self._build_ui()
        
    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)
        
        lbl_progress = QLabel("Progress")
        lbl_progress.setStyleSheet("color: #e8e8ed; font-size: 9.5pt; font-weight: 500;")
        lay.addWidget(lbl_progress)
        
        # Toggle
        toggle_lay = QHBoxLayout()
        toggle_lay.setContentsMargins(0, 0, 0, 0)
        self.toggle = _SegmentedToggle()
        self.toggle.btn_group.idClicked.connect(self._on_toggle)
        toggle_lay.addWidget(self.toggle)
        lay.addLayout(toggle_lay)
        
        # Navigator
        nav_lay = QHBoxLayout()
        nav_lay.setContentsMargins(0, 0, 0, 0)
        
        self.btn_prev = self._nav_arrow("‹")
        self.btn_next = self._nav_arrow("›")
        self.lbl_nav_date = QLabel()
        self.lbl_nav_date.setStyleSheet("color: #e8e8ed; font-size: 9.5pt; font-weight: 500;")
        
        self.btn_prev.clicked.connect(lambda: self._navigate(-1))
        self.btn_next.clicked.connect(lambda: self._navigate(1))
        
        nav_lay.addStretch(1)
        nav_lay.addWidget(self.btn_prev)
        nav_lay.addSpacing(16)
        nav_lay.addWidget(self.lbl_nav_date)
        nav_lay.addSpacing(16)
        nav_lay.addWidget(self.btn_next)
        nav_lay.addStretch(1)
        
        lay.addLayout(nav_lay)
        
        # Stacked Graph Area
        self.stack = QStackedWidget()
        self.stack.setFixedHeight(212)
        lay.addWidget(self.stack)
        
        # Legend
        leg_lay = QHBoxLayout()
        leg_lay.setContentsMargins(0, 16, 0, 0)
        leg_lay.setSpacing(16)
        
        leg_lay.addStretch(1)
        leg_lay.addWidget(self._legend_item("#e8e8ed", "Completed"))
        leg_lay.addWidget(self._legend_item("#323234", "Missed"))
        leg_lay.addStretch(1)
        
        lay.addLayout(leg_lay)
        
        self._update_view()
        
    def _nav_arrow(self, glyph: str) -> QPushButton:
        btn = QPushButton(glyph)
        btn.setFixedSize(24, 24)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ color: #636366; background-color: transparent; border: none; font-size: 14pt; padding: 0; }} "
            f"QPushButton:hover {{ color: #e8e8ed; }}"
        )
        return btn
        
    def _legend_item(self, color: str, text: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(6)
        
        dot = QWidget()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background: {color}; border-radius: 5px;")
        
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #888; font-size: 8pt;")
        
        lay.addWidget(dot)
        lay.addWidget(lbl)
        return w
        
    def _on_toggle(self, idx: int):
        self._update_view()
        
    def _navigate(self, direction: int):
        is_month = self.toggle.btn_group.checkedId() == 0
        if is_month:
            # month nav
            month = self.current_month_date.month - 1 + direction
            year = self.current_month_date.year + month // 12
            month = month % 12 + 1
            self.current_month_date = date(year, month, 1)
        else:
            # year nav
            self.current_year_date = self.current_year_date.replace(year=self.current_year_date.year + direction)
        
        self._update_view()
        
    def _update_view(self):
        is_month = self.toggle.btn_group.checkedId() == 0
        
        # clear stack
        while self.stack.count() > 0:
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()
            
        if is_month:
            self.lbl_nav_date.setText(self.current_month_date.strftime("%B %Y"))
            graph = _MonthCalendarGraph(self.current_month_date, self.created_date, self.completions)
        else:
            self.lbl_nav_date.setText(str(self.current_year_date.year))
            graph = _YearCalendarGraph(self.current_year_date, self.created_date, self.completions)
            
        # center graph
        wrap = QWidget()
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(1)
        lay.addWidget(graph)
        lay.addStretch(1)
        
        self.stack.addWidget(wrap)
