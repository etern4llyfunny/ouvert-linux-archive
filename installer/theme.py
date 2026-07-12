"""Тёмная тема в фирменных цветах PzhavOS (коралловый + бирюза)."""
from PySide6.QtWidgets import QApplication

C = {
    "bg": "#242424",
    "panel": "#2e2e2e",
    "fg": "#ececec",
    "muted": "#a0a0a0",
    "teal": "#5fd3c8",
    "coral": "#c67573",
    "line": "#3c3c3c",
}

QSS = f"""
* {{ font-family: "Noto Sans", "DejaVu Sans", sans-serif; font-size: 14px; }}
QMainWindow, QWidget {{ background: {C["bg"]}; color: {C["fg"]}; }}

QLabel#pageTitle {{ font-size: 24px; font-weight: 700; color: {C["teal"]}; background: transparent; }}
QLabel#muted {{ color: {C["muted"]}; background: transparent; }}
QLabel#stepLabel {{ color: {C["coral"]}; font-weight: 600; background: transparent; }}

QFrame#header {{ background: {C["panel"]}; border-bottom: 2px solid {C["coral"]}; }}
QFrame#header QLabel {{ background: transparent; }}

QPushButton {{
    background: {C["panel"]};
    border: 1px solid {C["coral"]};
    border-radius: 6px;
    padding: 8px 24px;
}}
QPushButton:hover {{ border-color: {C["teal"]}; color: {C["teal"]}; }}
QPushButton:disabled {{ color: {C["muted"]}; border-color: {C["line"]}; }}
QPushButton#primary {{ background: {C["coral"]}; color: #1d1d1d; font-weight: 600; border: none; }}
QPushButton#primary:hover {{ background: {C["teal"]}; color: #1d1d1d; }}

QLineEdit, QComboBox {{
    background: {C["panel"]};
    border: 1px solid {C["line"]};
    border-radius: 6px;
    padding: 7px 10px;
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {C["teal"]}; }}
QComboBox QAbstractItemView {{ background: {C["panel"]}; selection-background-color: {C["coral"]}; }}

QGroupBox {{
    border: 1px solid {C["line"]};
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px 10px 8px 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: {C["coral"]};
    font-weight: 600;
}}

QRadioButton {{ padding: 4px 2px; background: transparent; }}
QScrollArea {{ border: none; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(QSS)
