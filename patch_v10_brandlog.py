#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PzhavOS — патч v10: УБРАТЬ «Arch Linux» ИЗ ОКНА УСТАНОВЩИКА.

ПРОБЛЕМА: три INFO-строки archinstall, которые видит пользователь
(сняты с живого лога t24, 27.07.2026):
    Fetching Arch Linux package database...
    Waiting for Arch Linux keyring sync (archlinux-keyring-wkd-sync) to complete.
    Activating systemd-timesyncd ... using Arch Linux and ntp.org NTP servers

РЕШЕНИЕ: подмена ровно фразы «Arch Linux» (с пробелом, по границам слова)
на «PzhavOS».

ПОЧЕМУ НЕ ГЛОБАЛЬНЫЙ sed ПО СЛОВУ «arch» — в потоке есть РЕАЛЬНЫЕ имена:
    archlinux-keyring-wkd-sync   (имя systemd-юнита)
    /var/log/archinstall         (путь)
    arch-chroot                  (команда)
Тотальная замена превратила бы их в несуществующие сущности, и разбор
падений стал бы гаданием. Ни одно из них не содержит «Arch Linux» с
пробелом, поэтому правило безопасно.

ПОДМЕНА ТОЛЬКО ДЛЯ ПОКАЗА. В /tmp/pzhavos/install.log пишется СЫРОЙ текст:
разбирать падения по подделанному логу нельзя.

РАЗРЫВ НА ГРАНИЦЕ ЧТЕНИЯ: QProcess отдаёт поток кусками, фраза может
разорваться («...Arch Li» | «nux package...»). Поэтому хвост, который
является началом фразы, откладывается до следующего чтения (self._wbuf)
и досылается в _done, если процесс кончился.

СВОЙСТВА: транзакционный, идемпотентный, компилирует результат до записи.
ТРЕБУЕТ: уже применённый patch_v9_progress.py.

ЗАПУСК:  python3 patch_v10_brandlog.py [КОРЕНЬ_ПРОЕКТА]
"""

import sys
from pathlib import Path

# ─────────────────────────────── pages.py ───────────────────────────────

OLD_HINTS = '''# Общие фазы: подстрока -> ключ i18n.
_STAGE_HINTS = (
    ("fetching", "stage_db"),
    ("device modifications", "stage_disk"),
    ("fstab", "stage_fstab"),
    ("syncing", "stage_sync"),
)
'''

NEW_HINTS = '''# Общие фазы: подстрока -> ключ i18n.
_STAGE_HINTS = (
    ("fetching", "stage_db"),
    ("device modifications", "stage_disk"),
    ("fstab", "stage_fstab"),
    ("syncing", "stage_sync"),
)

# --- v10: брендинг вывода archinstall ---
# Меняем ТОЛЬКО фразу «Arch Linux» (с пробелом, по границам слова).
# НЕ трогаем archlinux-keyring-wkd-sync (юнит), /var/log/archinstall (путь),
# arch-chroot (команда) — в них пробела нет. Три строки, которые это чинит,
# сняты с живого лога t24: Fetching / keyring sync / NTP servers.
_BRAND_SRC = "Arch Linux"
_BRAND_DST = "PzhavOS"
_RE_BRAND = re.compile(r"\\bArch Linux\\b")


def _rebrand(text: str, carry: str = "") -> tuple[str, str]:
    """Подменяет бренд ТОЛЬКО для показа в окне (в файл лога идёт сырой текст).

    Поток приходит кусками, фраза может разорваться на границе чтения.
    Возвращает (готовый к показу текст, отложенный хвост).
    """
    text = carry + text
    keep = 0
    for n in range(min(len(_BRAND_SRC) - 1, len(text)), 0, -1):
        if _BRAND_SRC.startswith(text[-n:]):
            keep = n
            break
    if keep:
        return _RE_BRAND.sub(_BRAND_DST, text[:-keep]), text[-keep:]
    return _RE_BRAND.sub(_BRAND_DST, text), ""
'''

OLD_INIT = '        self._buf = ""          # хвост неполной строки между чтениями\n'
NEW_INIT = (
    '        self._buf = ""          # хвост неполной строки между чтениями\n'
    '        self._wbuf = ""         # v10: хвост на случай разрыва «Arch Linux»\n'
)

OLD_START = """        self._buf = ""
        self.bar.show()
"""
NEW_START = """        self._buf = ""
        self._wbuf = ""
        self.bar.show()
"""

OLD_APPEND = """        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(text)
        sb = self.log.verticalScrollBar()
"""
NEW_APPEND = """        shown, self._wbuf = _rebrand(text, self._wbuf)
        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(shown)
        sb = self.log.verticalScrollBar()
"""

OLD_DONE = """    def _done(self, code: int, _status) -> None:
        if self._logfile:
            self._logfile.close()
            self._logfile = None
"""
NEW_DONE = """    def _done(self, code: int, _status) -> None:
        if self._logfile:
            self._logfile.close()
            self._logfile = None
        if self._wbuf:                     # v10: досылаем отложенный хвост
            self.log.moveCursor(QTextCursor.MoveOperation.End)
            self.log.insertPlainText(self._wbuf)
            self._wbuf = ""
"""

EDITS = {
    "installer/pages.py": [
        ("функция _rebrand", OLD_HINTS, NEW_HINTS),
        ("буфер _wbuf в __init__", OLD_INIT, NEW_INIT),
        ("сброс _wbuf в start_install", OLD_START, NEW_START),
        ("подмена при показе в _append", OLD_APPEND, NEW_APPEND),
        ("досыл хвоста в _done", OLD_DONE, NEW_DONE),
    ],
}


def find_root(argv):
    if len(argv) > 1:
        return Path(argv[1]).expanduser().resolve()
    for cand in (Path.cwd(), Path.cwd() / "pzhavos", Path.home() / "pzhavos"):
        if (cand / "installer" / "pages.py").is_file():
            return cand.resolve()
    return None


def main():
    root = find_root(sys.argv)
    if root is None or not (root / "installer" / "pages.py").is_file():
        print("ОШИБКА: не найден installer/pages.py.")
        print("Запусти:  python3 patch_v10_brandlog.py /путь/к/pzhavos")
        return 1

    print(f"Корень проекта: {root}")
    print("─" * 70)

    planned = {}
    skipped = 0
    problems = []

    for rel, edits in EDITS.items():
        path = root / rel
        if not path.is_file():
            problems.append(f"{rel}: ФАЙЛ НЕ НАЙДЕН")
            continue
        text = path.read_text(encoding="utf-8")
        orig = text
        for name, old, new in edits:
            if new in text:
                print(f"  = {rel}: «{name}» уже применён")
                skipped += 1
                continue
            n = text.count(old)
            if n != 1:
                problems.append(
                    f"{rel}: якорь «{name}» найден {n} раз (нужно ровно 1). "
                    "Сначала применён ли patch_v9_progress.py?")
                continue
            text = text.replace(old, new, 1)
            print(f"  + {rel}: «{name}» — применяю")
        if text != orig:
            try:
                compile(text, str(path), "exec")
            except SyntaxError as e:
                problems.append(f"{rel}: результат НЕ КОМПИЛИРУЕТСЯ: {e}")
                continue
            planned[path] = text

    print("─" * 70)
    if problems:
        print("ОТКАТ. Ни один файл НЕ изменён. Причины:")
        for p in problems:
            print(f"  ! {p}")
        return 2

    if not planned:
        print(f"Изменений нет — всё уже на месте ({skipped} пунктов). OK.")
        return 0

    for path, text in planned.items():
        bak = path.with_suffix(path.suffix + ".v10bak")
        if not bak.exists():
            bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.write_text(text, encoding="utf-8")
        print(f"  ЗАПИСАН: {path}  (бэкап: {bak.name})")

    print("─" * 70)
    print("ГОТОВО. Бэкапы .v10bak убери из installer/ перед сборкой ISO!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
