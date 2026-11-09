"""Тёмная тема в фирменных цветах Ouvert Linux.

Голубой — основной акцент: заголовки, фокус, главная кнопка.
Коралловый — только опасное и ошибки, чтобы «Стереть диск» не выглядело
так же, как «Далее».
"""
from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QApplication, QPushButton

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

QPushButton#primary {{ background: {C["blue"]}; color: {C["ink"]}; font-weight: 600; border: 2px solid transparent; }}
QPushButton#primary:hover {{ background: {C["coral"]}; color: {C["ink"]}; }}
QPushButton#primary:disabled {{ background: {C["line"]}; color: {C["muted"]}; }}

/* необратимое: разметка, форматирование, стирание диска */
QPushButton#danger {{ background: {C["coral"]}; color: {C["ink"]}; font-weight: 600; border: 2px solid transparent; }}
QPushButton#danger:hover {{ background: #E04B3A; }}

/* Патч 71 (Bug 72): рамка фокуса — только с клавиатуры, как у логотипа (73.1).
   Свойство kbfocus ставит фильтр из apply_theme(); пунктир Qt не рисуем. */
QPushButton {{ outline: none; }}
QPushButton[kbfocus="true"] {{ border-color: {C["blue"]}; }}
QPushButton#primary[kbfocus="true"], QPushButton#danger[kbfocus="true"] {{ border-color: {C["fg"]}; }}

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
/* Патч 71: свой кружок — штатный рисовался цветом фона, и невыбранные
   пункты было не отличить от простого текста */
QRadioButton::indicator {{ width: 12px; height: 12px; border: 2px solid {C["muted"]}; border-radius: 8px; background: transparent; }}
QRadioButton::indicator:hover {{ border-color: {C["blue_hi"]}; }}
QRadioButton::indicator:checked {{ border-color: {C["blue"]}; background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 {C["blue"]}, stop:0.5 {C["blue"]}, stop:0.6 transparent); }}
QRadioButton::indicator:disabled {{ border-color: {C["line"]}; }}
/* Патч 74 (Bug 76): свой квадрат у галок — штатный рисовался цветом фона.
   Выбранная — сплошная голубая заливка, без svg: в live его может не быть */
QCheckBox {{ background: transparent; }}
QCheckBox::indicator {{ width: 12px; height: 12px; border: 2px solid {C["muted"]}; border-radius: 4px; background: transparent; }}
QCheckBox::indicator:hover {{ border-color: {C["blue_hi"]}; }}
QCheckBox::indicator:checked {{ border-color: {C["blue"]}; background: {C["blue"]}; }}
QCheckBox::indicator:disabled {{ border-color: {C["line"]}; }}
QCheckBox::indicator:checked:disabled {{ background: {C["line"]}; }}
QScrollArea {{ border: none; }}
/* Патч 71: тонкий скроллбар без кнопок-стрелок */
QScrollBar {{ background: transparent; border: none; margin: 0; }}
QScrollBar:vertical {{ width: 10px; }}
QScrollBar:horizontal {{ height: 10px; }}
QScrollBar::handle {{ background: rgba(147, 162, 177, 0.35); border-radius: 4px; margin: 1px; }}
QScrollBar::handle:hover {{ background: {C["muted"]}; }}
QScrollBar::handle:vertical {{ min-height: 28px; }}
QScrollBar::handle:horizontal {{ min-width: 28px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; background: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

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


class _KbFocus(QObject):
    """Патч 71 (Bug 72): свойство kbfocus у кнопки — только когда фокус
    пришёл с клавиатуры (Tab/Shift+Tab); клик мышью его гасит. С голым
    :focus рамка висела бы на «Далее» после каждого клика."""

    _WATCH = (QEvent.Type.FocusIn, QEvent.Type.FocusOut, QEvent.Type.MouseButtonPress)

    def eventFilter(self, obj, ev) -> bool:
        t = ev.type()
        if t in self._WATCH and isinstance(obj, QPushButton):
            kb = t == QEvent.Type.FocusIn and ev.reason() in (
                Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason)
            if bool(obj.property("kbfocus")) != kb:
                obj.setProperty("kbfocus", kb)
                obj.style().unpolish(obj)
                obj.style().polish(obj)
        return False


_KB = _KbFocus()


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(QSS)
    app.installEventFilter(_KB)
