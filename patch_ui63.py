#!/usr/bin/env python3
"""Патч 63 — установщик на одном мониторе + диалоги внутри окна.

Bug 57: под cage (режим extend) окно растянуто на ВСЕ мониторы, а сдвинуть
своё окно Wayland-клиент не может. Лечение: панель установщика рисуется
в прямоугольнике ОДНОГО экрана (больше пикселей → больше дюймов → первый),
по центру, не больше 920×640 (п. 2.6 — вёрстка больше не разъезжается).

Bug 62 + стык мониторов: каждый QMessageBox/QDialog — отдельное окно,
cage ставит его по центру всей раскладки (на стык) и с рамкой _ □ ✕.
Лечение: новый overlay.py встраивает диалог в окно — затемнение + карточка.

Файлы (обе копии): wizard.py, partedit.py, partitioning.py, theme.py
+ новый overlay.py. main.py НЕ трогается.

Двухпроходный: всё считается в памяти; пишется, только если ВСЕ файлы
обеих копий прошли якоря (точный счёт), компиляцию и сверку копий.
Бэкапов нет намеренно — бэкап это git: патчер требует, чтобы файлы
совпадали с HEAD. Откат печатается в конце.
Идемпотентный: повторный запуск ничего не пишет.

Запуск: python ~/pzhavos/patch_ui63.py
"""
import subprocess
import sys
from pathlib import Path

BASE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.home() / "pzhavos"
COPIES = [
    BASE / "installer",
    BASE / "iso/profile/airootfs/opt/ouvert-installer",
]
FILES = ["wizard.py", "partedit.py", "partitioning.py", "theme.py"]
MARK = "Патч 63"

OVERLAY = '''"""Патч 63: диалоги внутри окна установщика.

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
'''

WIZ_ROOT_OLD = '''        root = QWidget()
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(header)
        v.addWidget(self.stack, 1)
        v.addLayout(nav)
        self.setCentralWidget(root)
'''
WIZ_ROOT_NEW = '''        # Патч 63: панель — ребёнок пустого центрального виджета, ставится
        # вручную в _place(). Под cage окно растянуто на все мониторы
        # (Bug 57), сдвинуть окно Wayland-клиент не может — только нарисовать
        # себя в нужном прямоугольнике.
        outer = QWidget()
        self.panel = QWidget(outer)
        self.panel.setObjectName("panel")
        self.panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        v = QVBoxLayout(self.panel)
        v.setContentsMargins(1, 1, 1, 1)  # рамка панели из theme.py
        v.setSpacing(0)
        v.addWidget(header)
        v.addWidget(self.stack, 1)
        v.addLayout(nav)
        self.setCentralWidget(outer)
        self.area = QRect()      # прямоугольник выбранного экрана, для overlay
        overlay.HOST = self      # диалоги — внутрь окна (overlay.py)
'''
WIZ_PLACE = '''    # --- Патч 63: геометрия ---
    PANEL = QSize(920, 640)  # под этот размер свёрстаны все страницы

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place()

    def _place(self) -> None:
        """Панель — в прямоугольник одного экрана, по центру, не больше PANEL."""
        self.area = self.centralWidget().rect()
        screens = QGuiApplication.screens()
        if len(screens) > 1 and (
            self.width() > max(s.geometry().width() for s in screens)
            or self.height() > max(s.geometry().height() for s in screens)
        ):
            # окно больше любого экрана — cage растянул его на все (extend).
            # Экран: больше пикселей → больше дюймов → первый по списку.
            box = QRect()
            for s in screens:
                box = box.united(s.geometry())
            best = max(screens, key=lambda s: (
                s.geometry().width() * s.geometry().height(),
                s.physicalSize().width() * s.physicalSize().height(),
            ))
            self.area = best.geometry().translated(-box.topLeft())
            print(f"ouvert: окно {self.width()}x{self.height()}, экраны "
                  + ", ".join(f"{s.name()} {s.geometry().getRect()}" for s in screens)
                  + f" -> {best.name()}", file=sys.stderr)
        size = self.PANEL.boundedTo(self.area.size())
        a = self.area
        self.panel.setGeometry(a.x() + (a.width() - size.width()) // 2,
                               a.y() + (a.height() - size.height()) // 2,
                               size.width(), size.height())

    # --- логика ---
'''

THEME_OLD = '''QScrollArea {{ border: none; }}
"""'''
THEME_NEW = '''QScrollArea {{ border: none; }}

/* Патч 63: панель установщика и диалоги внутри окна (overlay.py) */
QWidget#panel {{ border: 1px solid {C["line"]}; }}
QWidget#scrim {{ background: rgba(0, 0, 0, 150); }}
QWidget#scrim > QDialog {{ border: 1px solid {C["line"]}; border-radius: 8px; }}
"""'''


class Fail(Exception):
    pass


def sub(src: str, old: str, new: str, n: int, where: str) -> str:
    c = src.count(old)
    if c != n:
        raise Fail(f"{where}: якорь {old.strip()[:60]!r} найден {c} раз, ждали {n}")
    return src.replace(old, new)


def edit_wizard(s: str) -> str:
    w = "wizard.py"
    s = sub(s, "from PySide6.QtCore import QProcess, Qt\n",
            "from PySide6.QtCore import QProcess, QRect, QSize, Qt\n", 1, w)
    s = sub(s, "from PySide6.QtGui import QPixmap\n",
            "from PySide6.QtGui import QGuiApplication, QPixmap\n", 1, w)
    s = sub(s, "from pathlib import Path\n",
            "import sys\nfrom pathlib import Path\n", 1, w)
    s = sub(s, "from config_gen import write_configs\n",
            "import overlay\nfrom config_gen import write_configs\n", 1, w)
    s = sub(s, WIZ_ROOT_OLD, WIZ_ROOT_NEW, 1, w)
    s = sub(s, "    # --- логика ---\n", WIZ_PLACE, 1, w)
    s = sub(s, "QMessageBox.warning(", "overlay.say(", 6, w)
    s = sub(s, 'QMessageBox.information(self, "Ouvert Linux", tr("not_live"))',
            'overlay.say(self, "Ouvert Linux", tr("not_live"), QMessageBox.Icon.Information)', 1, w)
    s = sub(s, "        box.exec()\n", "        overlay.run(box)\n", 1, w)
    return s


def edit_partedit(s: str) -> str:
    w = "partedit.py"
    opener = "from PySide6.QtWidgets import (\n"
    if s.count(opener) != 1:
        raise Fail(f"{w}: якорь {opener.strip()!r} найден {s.count(opener)} раз, ждали 1")
    close = s.find("\n)\n", s.index(opener))
    if close < 0:
        raise Fail(f"{w}: не найдена закрывающая скобка импорта PySide6")
    s = s[:close + 3] + "\nimport overlay\n" + s[close + 3:]
    s = sub(s, 'QMessageBox.critical(self, tr("pe_err_title"), str(exc))',
            'overlay.say(self, tr("pe_err_title"), str(exc), QMessageBox.Icon.Critical)', 1, w)
    s = sub(s, "QMessageBox.warning(", "overlay.say(", 2, w)
    s = sub(s, "box.exec()", "overlay.run(box)", 2, w)
    s = sub(s, "dlg.exec()", "overlay.run(dlg)", 1, w)
    return s


def edit_partitioning(s: str) -> str:
    w = "partitioning.py"
    s = sub(s, "        from PySide6.QtWidgets import QMessageBox\n",
            "        import overlay\n        from PySide6.QtWidgets import QMessageBox\n", 1, w)
    s = sub(s, "QMessageBox.warning(", "overlay.say(", 1, w)
    s = sub(s, 'QMessageBox.critical(self, tr("part_title"), f"partedit: {exc}")',
            'overlay.say(self, tr("part_title"), f"partedit: {exc}", QMessageBox.Icon.Critical)', 1, w)
    s = sub(s, "PartitionEditor(disk, self).exec()",
            "overlay.run(PartitionEditor(disk, self))", 1, w)
    return s


def edit_theme(s: str) -> str:
    return sub(s, THEME_OLD, THEME_NEW, 1, "theme.py")


EDITS = {"wizard.py": edit_wizard, "partedit.py": edit_partedit,
         "partitioning.py": edit_partitioning, "theme.py": edit_theme}


def main() -> int:
    print(f"Патч 63 — база {BASE}")
    for d in COPIES:
        if not d.is_dir():
            print(f"✘ нет каталога {d}")
            return 1

    # --- идемпотентность ---
    done = [(d / "overlay.py").exists() and MARK in (d / "wizard.py").read_text(encoding="utf-8")
            for d in COPIES]
    if all(done):
        print("✔ Патч 63 уже применён в обеих копиях — ничего не пишу.")
        return 0
    if any(done):
        print("✘ Патч 63 применён только в одной копии — разбирайся руками.")
        return 1

    # --- проход 1: всё в памяти ---
    rel = [str(d.relative_to(BASE) / f) for d in COPIES for f in FILES]
    r = subprocess.run(["git", "-C", str(BASE), "diff", "--quiet", "HEAD", "--", *rel])
    if r.returncode != 0:
        print("✘ файлы отличаются от HEAD — откат через git был бы нечестным. Сначала коммит.")
        return 1
    for d in COPIES:
        if (d / "overlay.py").exists():
            print(f"✘ {d / 'overlay.py'} уже есть, а метки патча нет — разбирайся руками.")
            return 1

    src = {f: (COPIES[0] / f).read_bytes() for f in FILES}
    for f in FILES:
        if (COPIES[1] / f).read_bytes() != src[f]:
            print(f"✘ копии {f} расходятся ДО патча — стоп.")
            return 1

    try:
        new = {f: EDITS[f](src[f].decode("utf-8")) for f in FILES}
    except Fail as e:
        print(f"✘ {e}\n  НИЧЕГО НЕ ЗАПИСАНО.")
        return 1
    new["overlay.py"] = OVERLAY
    for f, text in new.items():
        try:
            compile(text, f, "exec")
        except SyntaxError as e:
            print(f"✘ {f} не компилируется после правки: {e}\n  НИЧЕГО НЕ ЗАПИСАНО.")
            return 1

    # --- проход 2: запись ---
    for d in COPIES:
        for f, text in new.items():
            (d / f).write_bytes(text.encode("utf-8"))

    # --- сверка ---
    ok = True
    print("\nРАЗМЕРЫ, байты (было → стало):")
    for f, text in new.items():
        b = text.encode("utf-8")
        got = [(d / f).read_bytes() for d in COPIES]
        same = all(g == b for g in got)
        ok &= same
        was = len(src[f]) if f in src else 0
        print(f"  {f:16} {was:6} → {len(b):6}  {'обе копии ✔' if same else '✘ РАСХОЖДЕНИЕ'}")
    if not ok:
        print("✘ записанное не совпало с рассчитанным!")
        return 1
    print("\n✔ Патч 63 применён.")
    print("ОТКАТ: git -C ~/pzhavos checkout -- installer iso/profile/airootfs/opt/ouvert-installer"
          " && rm ~/pzhavos/installer/overlay.py"
          " ~/pzhavos/iso/profile/airootfs/opt/ouvert-installer/overlay.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
