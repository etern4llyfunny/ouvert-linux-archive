#!/usr/bin/env python3
"""
patch_bug24_v2.py — PzhavOS, ИСПРАВЛЕНИЕ первой редакции патча Bug 24.

ЧТО БЫЛО НЕ ТАК В v1:
    Блок восстановления делал self.mount.setCurrentIndex(...) ПЕРВЫМ.
    В Qt это испускает currentIndexChanged -> вызывается _changed(),
    который читает ЕЩЁ НЕ ВОССТАНОВЛЕННЫЕ self.fmt / self.fs (пустые)
    и записывает их в part["format"] / part["fs"], затирая сохранённое.
    Следующие строки блока читали уже испорченные значения.
    Итог: точка монтирования переживала возврат, а ФС и галка «Форматировать» — нет.
    (Подтверждено живьём в GUI: /home уцелел, btrfs -> ext4, галка слетела.)

ЧТО ДЕЛАЕТ v2:
    1) СНАЧАЛА считывает все три значения из part[] в локальные переменные;
    2) ПОТОМ выставляет виджеты под blockSignals(True/False), чтобы ни один
       промежуточный _changed() не сработал;
    3) финальный _changed() (он был и остаётся) один раз приводит part[]
       в согласованное состояние.

Требует, чтобы patch_bug24.py (v1) был уже применён.
Свойства: транзакционный, идемпотентный, с бэкапом, с compile() до записи.
ПАТЧИТ ТОЛЬКО installer/ — ISO-профиль синхронизирует build.sh (rsync).
"""

import ast
import datetime
import shutil
import sys
from pathlib import Path

MARKER_V2 = "Bug 24 v2"

TARGET_DEFAULT = Path.home() / "pzhavos" / "installer" / "partitioning.py"

OLD = '''        # --- Bug 24: восстановить назначения из part[] ДО _changed(),
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
'''

NEW = '''        # --- Bug 24 v2: восстановить назначения из part[] ДО _changed().
        # ПОРЯДОК КРИТИЧЕН: сначала СЧИТАТЬ все три значения, потом ставить
        # виджеты под blockSignals. Иначе setCurrentIndex испустит сигнал,
        # дёрнет _changed(), и тот затрёт part[] значениями ещё не
        # восстановленных комбобоксов (ошибка первой редакции патча). ---
        _mp = part.get("mountpoint")
        _fs_saved = part.get("fs")
        _fmt_saved = bool(part.get("format"))
        if _mp is not None:
            _i = self.mount.findData(_mp)
            if _i >= 0:
                self.mount.blockSignals(True)
                self.mount.setCurrentIndex(_i)
                self.mount.blockSignals(False)
        if _fs_saved:
            _i = self.fs.findText(_fs_saved)
            if _i >= 0:
                self.fs.blockSignals(True)
                self.fs.setCurrentIndex(_i)
                self.fs.blockSignals(False)
        if _fmt_saved:
            self.fmt.blockSignals(True)
            self.fmt.setChecked(True)
            self.fmt.blockSignals(False)
        # --- конец Bug 24 v2 ---
'''


def fail(msg):
    print("ОШИБКА: " + msg)
    print("Файл НЕ изменён.")
    sys.exit(1)


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET_DEFAULT
    if not target.is_file():
        fail(f"не найден файл {target}")

    src = target.read_text(encoding="utf-8")

    if MARKER_V2 in src:
        print(f"{target}: уже пропатчен v2 (найден маркер «{MARKER_V2}»).")
        print("Файл НЕ изменён. Выход 0.")
        return 0

    n = src.count(OLD)
    if n != 1:
        fail(f"блок Bug 24 v1 найден {n} раз(а), ожидалась ровно 1. "
             "Сначала должен быть применён patch_bug24.py.")
    print("Блок первой редакции найден ровно один раз.")

    new = src.replace(OLD, NEW, 1)

    try:
        compile(new, str(target), "exec")
        ast.parse(new)
    except SyntaxError as e:
        fail(f"результат не компилируется: {e}")
    print("Синтаксис результата проверен (compile + ast).")

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = target.with_suffix(target.suffix + f".bug24v2bak-{stamp}")
    shutil.copy2(target, backup)
    target.write_text(new, encoding="utf-8")

    print(f"Бэкап:  {backup}")
    print(f"Патч v2 применён: {target}")
    print(f"Строк было {len(src.splitlines())}, стало {len(new.splitlines())}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
