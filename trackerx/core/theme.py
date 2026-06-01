from __future__ import annotations


LIGHT_THEME = """
QWidget { background: #ffffff; color: #111111; font-size: 11pt; }
QMainWindow, QDialog { background: #ffffff; }
QFrame#SideBar { background: #f0f0f0; border-right: 1px solid #dcdcdc; }
QLabel#Brand { color: #111111; font-size: 17pt; font-weight: 700; background: transparent; }
QListWidget#NavList { background: #f0f0f0; border: none; color: #111111; outline: 0; }
QListWidget#NavList::item { padding: 10px 12px; border-radius: 8px; margin: 2px 0; }
QListWidget#NavList::item:selected { background: #e0e0e0; color: #111111; }
QListWidget#NavList::item:hover { background: #e8e8e8; color: #111111; }
QFrame#Card { background: #ffffff; border-radius: 14px; border: 1px solid #d0d0d0; }
QPushButton { background: #d0d0d0; color: #111111; border: none; border-radius: 10px; padding: 8px 12px; }
QPushButton:hover { background: #c0c0c0; }
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit { background: #ffffff; border: 1px solid #a0a0a0; border-radius: 8px; padding: 6px; color: #111111; }
QListWidget, QTreeWidget, QTableWidget { background: #ffffff; border: 1px solid #c0c0c0; color: #111111; }
QCalendarWidget QWidget { background: #ffffff; color: #111111; }
"""


DARK_THEME = """
QWidget { background: #111111; color: #f5f5f5; font-size: 11pt; }
QMainWindow, QDialog { background: #111111; }
QFrame#SideBar { background: #1a1a1a; border-right: 1px solid #333333; }
QLabel#Brand { color: #ffffff; font-size: 17pt; font-weight: 700; background: transparent; }
QListWidget#NavList { background: #1a1a1a; border: none; color: #d4d4d4; outline: 0; }
QListWidget#NavList::item { padding: 10px 12px; border-radius: 8px; margin: 2px 0; }
QListWidget#NavList::item:selected { background: #333333; color: #ffffff; }
QListWidget#NavList::item:hover { background: #2a2a2a; color: #ffffff; }
QFrame#Card { background: #1a1a1a; border-radius: 14px; border: 1px solid #404040; }
QPushButton { background: #333333; color: #ffffff; border: none; border-radius: 10px; padding: 8px 12px; }
QPushButton:hover { background: #444444; }
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit { background: #1a1a1a; border: 1px solid #4b5563; border-radius: 8px; padding: 6px; color: #ffffff; }
QListWidget, QTreeWidget, QTableWidget { background: #1a1a1a; border: 1px solid #4b5563; color: #ffffff; }
QCalendarWidget QWidget { background: #1a1a1a; color: #ffffff; }
"""
