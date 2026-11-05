"""Тёмная тема в фирменных цветах Ouvert Linux.

Голубой — основной акцент: заголовки, фокус, главная кнопка.
Коралловый — только опасное и ошибки, чтобы «Стереть диск» не выглядело
так же, как «Далее».
"""
from PySide6.QtWidgets import QApplication

C = {
    "bg": "#14191F",
    "panel": "#1C232B",
    "fg": "#E8EDF2",
    "muted": "#93A2B1",
    "blue": "#2E9FF0",
    "blue_hi": "#57B4FF",
    "coral": "#FF6A5C",
    "ink": "#08121C",
    "line": "#2A333D",
}

QSS = f"""
/* латиница из Sora, кириллица из Onest, остальное добирает Noto */
* {{ font-family: "Sora", "Onest", "Noto Sans", "DejaVu Sans", sans-serif; font-size: 14px; }}
QMainWindow, QWidget {{ background: {C["bg"]}; color: {C["fg"]}; }}

QLabel#pageTitle {{ font-size: 24px; font-weight: 700; color: {C["blue"]}; background: transparent; }}
QLabel#muted {{ color: {C["muted"]}; background: transparent; }}
QLabel#stepLabel {{ color: {C["muted"]}; font-weight: 600; background: transparent; }}
QLabel#warning {{ color: {C["coral"]}; font-weight: 600; background: transparent; }}

QFrame#header {{ background: {C["panel"]}; border-bottom: 2px solid {C["coral"]}; }}
QFrame#header QLabel {{ background: transparent; }}

QPushButton {{
    background: {C["panel"]};
    border: 1px solid {C["line"]};
    border-radius: 6px;
    padding: 8px 24px;
}}
QPushButton:hover {{ border-color: {C["coral"]}; color: {C["coral"]}; }}
QPushButton:disabled {{ color: {C["muted"]}; border-color: {C["line"]}; }}

QPushButton#primary {{ background: {C["blue"]}; color: {C["ink"]}; font-weight: 600; border: none; }}
QPushButton#primary:hover {{ background: {C["coral"]}; color: {C["ink"]}; }}
QPushButton#primary:disabled {{ background: {C["line"]}; color: {C["muted"]}; }}

/* необратимое: разметка, форматирование, стирание диска */
QPushButton#danger {{ background: {C["coral"]}; color: {C["ink"]}; font-weight: 600; border: none; }}
QPushButton#danger:hover {{ background: #E04B3A; }}

QLineEdit, QComboBox {{
    background: {C["panel"]};
    border: 1px solid {C["line"]};
    border-radius: 6px;
    padding: 7px 10px;
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {C["blue"]}; }}
QLineEdit[invalid="true"] {{ border-color: {C["coral"]}; }}
QComboBox QAbstractItemView {{ background: {C["panel"]}; selection-background-color: {C["blue"]}; selection-color: {C["ink"]}; }}

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
    color: {C["blue"]};
    font-weight: 600;
}}

QProgressBar {{ background: {C["panel"]}; border: 1px solid {C["line"]}; border-radius: 6px; text-align: center; }}
QProgressBar::chunk {{ background: {C["blue"]}; border-radius: 5px; }}

QRadioButton {{ padding: 4px 2px; background: transparent; }}
QScrollArea {{ border: none; }}

/* Патч 73: меню логотипа — свой фон и рамка, иначе правило QWidget выше
   красит его цветом страницы и пункты висят прямо поверх текста */
QMenu {{ background: {C["panel"]}; border: 1px solid {C["line"]}; padding: 6px; }}
QMenu::item {{ background: transparent; padding: 8px 28px 8px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: rgba(46, 159, 240, 0.18); color: {C["fg"]}; }}
QMenu::separator {{ height: 1px; background: {C["line"]}; margin: 4px 8px; }}

/* Патч 63: панель установщика и диалоги внутри окна (overlay.py) */
QWidget#panel {{ border: 1px solid {C["line"]}; }}
QWidget#scrim {{ background: rgba(0, 0, 0, 150); }}
QWidget#scrim > QDialog {{ border: 1px solid {C["line"]}; border-radius: 8px; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(QSS)
