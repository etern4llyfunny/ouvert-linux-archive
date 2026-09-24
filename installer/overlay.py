"""Патч 63: диалоги внутри окна установщика.

Под cage каждый QDialog — отдельное окно, и cage ставит его по центру
ВСЕЙ раскладки: на двух мониторах — ровно на стык (Bug 57), да ещё
с рамкой _ □ ✕ (Bug 62). Сдвинуть своё окно Wayland-клиент не может,
поэтому диалог встраивается в окно установщика: затемнение на выбранный
экран + карточка по центру.

HOST ставит InstallerWindow (нужны .centralWidget() и .area). Без него
(stand_gui, тесты) — обычный exec(), как раньше.
"""
from PySide6.QtCore import QEventLoop, Qt
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

HOST = None


def run(dlg: QDialog) -> int:
    """Замена dlg.exec(): тот же код возврата, но внутри окна."""
    if HOST is None:
        return dlg.exec()
    outer = HOST.centralWidget()
    # всё, что уже на экране (панель, диалоги ниже по стопке), глушим:
    # иначе Tab уведёт фокус на «Далее» за затемнением
    others = [w for w in outer.children()
              if isinstance(w, QWidget) and w.isEnabled()]
    scrim = QWidget(outer)
    scrim.setObjectName("scrim")
    scrim.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    # ponytail: геометрия снимается один раз; ресайз окна при открытом
    # диалоге затемнение не догонит — в киоске окно не ресайзится
    scrim.setGeometry(HOST.area)
    parent, flags = dlg.parentWidget(), dlg.windowFlags()
    dlg.setParent(scrim, Qt.WindowType.Widget)
    dlg.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    for w in others:
        w.setEnabled(False)
    scrim.show()
    scrim.raise_()
    dlg.show()
    size = dlg.size().boundedTo(scrim.size())
    dlg.setGeometry((scrim.width() - size.width()) // 2,
                    (scrim.height() - size.height()) // 2,
                    size.width(), size.height())
    btn = None
    if isinstance(dlg, QMessageBox):
        btn = dlg.defaultButton() or next(iter(dlg.buttons()), None)
    (btn or dlg).setFocus()
    loop = QEventLoop()
    dlg.finished.connect(loop.quit)
    loop.exec()
    for w in others:
        w.setEnabled(True)
    dlg.setParent(parent, flags)  # как после обычного exec(): скрытое окно
    # сразу, не deleteLater: иначе следующий run() успеет «заглушить»
    # полуживое затемнение, и Qt удалит его у нас из-под рук
    scrim.hide()
    scrim.setParent(None)
    return dlg.result()


def say(parent, title: str, text: str,
        icon=QMessageBox.Icon.Warning) -> None:
    """Замена QMessageBox.warning/critical/information."""
    box = QMessageBox(icon, title, text, QMessageBox.StandardButton.Ok, parent)
    run(box)
    box.deleteLater()
