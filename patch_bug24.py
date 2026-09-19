#!/usr/bin/env python3
"""
patch_bug24.py — PzhavOS, Bug 24.

ПРОБЛЕМА: PartitioningPage.on_enter() безусловно зовёт _reload_parts(),
который перезаписывает state["manual_parts"] свежим списком с диска.
Возврат «Назад» на страницу разметки стирает все назначения юзера.
Плюс ManualRow.__init__ в конце зовёт _changed(), который затирает
значения в part[] значениями пустых комбобоксов.

ЛЕЧЕНИЕ (две правки):
  1. _reload_parts: слить старые назначения со свежим списком по ключу
     part["path"]. Переносятся mountpoint / format / fs.
     ТОЛЬКО если диск тот же — иначе назначения устарели и их надо
     выбросить осознанно (защита от «выбрал другой диск, а точки
     монтирования остались от старого»).
  2. ManualRow.__init__: восстановить состояние виджетов из part[]
     ДО финального _changed().

Свойства: транзакционный (проверяет ВСЕ якоря до записи), идемпотентный,
с бэкапом, с compile() до записи.

ПАТЧИТ ТОЛЬКО installer/ — ISO-профиль синхронизирует build.sh (rsync).
"""

import ast
import datetime
import shutil
import sys
from pathlib import Path

MARKER = "Bug 24"

TARGET_DEFAULT = Path.home() / "pzhavos" / "installer" / "partitioning.py"

# --- Якорь 1: запись свежего списка в state -----------------------------
A1 = '        self.state["manual_parts"] = parts\n'

A1_NEW = '''        # --- Bug 24: сохранить назначения юзера при возврате «Назад» ---
        # Переносим mountpoint/format/fs со старого списка на свежий по
        # ключу path. Только если диск ТОТ ЖЕ: иначе назначения устарели.
        if self.state.get("manual_parts_disk") == disk:
            _saved = {
                _p.get("path"): _p
                for _p in (self.state.get("manual_parts") or [])
                if _p.get("path")
            }
            for _p in parts:
                _old = _saved.get(_p.get("path"))
                if not _old:
                    continue
                for _k in ("mountpoint", "format", "fs"):
                    if _k in _old:
                        _p[_k] = _old[_k]
        self.state["manual_parts_disk"] = disk
        # --- конец Bug 24 ---
        self.state["manual_parts"] = parts
'''

# --- Якорь 2: финальный вызов в ManualRow.__init__ ----------------------
A2 = "        row.addStretch()\n        self._changed()\n"

A2_NEW = '''        row.addStretch()
        # --- Bug 24: восстановить назначения из part[] ДО _changed(),
        # иначе _changed() затрёт их значениями пустых комбобоксов ---
        _mp = part.get("mountpoint")
        if _mp is not None:
            _i = self.mount.findData(_mp)
            if _i >= 0:
                self.mount.setCurrentIndex(_i)
        _fs = part.get("fs")
        if _fs:
            _i = self.fs.findText(_fs)
            if _i >= 0:
                self.fs.setCurrentIndex(_i)
        if part.get("format"):
            self.fmt.setChecked(True)
        # --- конец Bug 24 ---
        self._changed()
'''

EDITS = [("state[\"manual_parts\"] = parts", A1, A1_NEW),
         ("ManualRow.__init__ / _changed()", A2, A2_NEW)]


def fail(msg):
    print("ОШИБКА: " + msg)
    print("Файл НЕ изменён.")
    sys.exit(1)


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET_DEFAULT
    if not target.is_file():
        fail(f"не найден файл {target}")

    src = target.read_text(encoding="utf-8")

    # --- идемпотентность ---
    if MARKER in src:
        print(f"{target}: уже пропатчен (найден маркер «{MARKER}»).")
        print("Файл НЕ изменён. Выход 0.")
        return 0

    # --- ТРАНЗАКЦИОННОСТЬ: проверить ВСЕ якоря ДО любой записи ---
    for name, anchor, _ in EDITS:
        n = src.count(anchor)
        if n != 1:
            fail(f"якорь [{name}] найден {n} раз(а), ожидалась ровно 1.")
    print("Все якоря найдены ровно по одному разу.")

    new = src
    for _, anchor, repl in EDITS:
        new = new.replace(anchor, repl, 1)

    # --- самопроверка синтаксиса ДО записи ---
    try:
        compile(new, str(target), "exec")
        ast.parse(new)
    except SyntaxError as e:
        fail(f"результат не компилируется: {e}")
    print("Синтаксис результата проверен (compile + ast).")

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = target.with_suffix(target.suffix + f".bug24bak-{stamp}")
    shutil.copy2(target, backup)
    target.write_text(new, encoding="utf-8")

    print(f"Бэкап:  {backup}")
    print(f"Патч применён: {target}")
    print(f"Строк было {len(src.splitlines())}, стало {len(new.splitlines())}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
