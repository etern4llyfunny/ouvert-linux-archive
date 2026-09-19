#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PzhavOS — патч v8, часть 2: БРЕНДИНГ LIVE-СРЕДЫ (tty).

Правит ТОЛЬКО ISO-профиль (iso/profile/airootfs/etc/). Установщика не касается.

  1) motd     — перезаписывается: вместо «To install Arch Linux follow the
                installation guide…» — подсказки PzhavOS.
  2) issue    — создаётся: «PzhavOS \\r (\\l)» вместо стокового
                «Arch Linux \\r (\\l)» (пакет filesystem). Это та самая строка
                «Arch Linux 7.1.5-arch1-1 (tty1)» над приглашением логина.
  3) os-release — создаётся. Именно отсюда systemd берёт PRETTY_NAME и печатает
                при загрузке «Welcome to Arch Linux!». Содержимое совпадает
                с тем, что config_gen.py пишет в УСТАНОВЛЕННУЮ систему.

ПОЧЕМУ ТЕКСТ АНГЛИЙСКИЙ: в live-tty стоит дефолтный шрифт консоли без
кириллицы (в профиле нет vconsole.conf). Русский текст превратился бы в кашу.

РИСК, ЗАФИКСИРОВАТЬ: os-release в live меняет ID на pzhavos (ID_LIKE=arch
сохранён). archinstall на дистрибутив не завязан, но путь НЕ проверялся.
Если на t21 в live всплывёт странность — подозревать в первую очередь этот
файл; откат = удалить iso/profile/airootfs/etc/os-release.

СВОЙСТВА: транзакционный, идемпотентный, бэкапит существующие файлы (.v8bak).

ЗАПУСК:  python3 patch_v8_livetty.py [КОРЕНЬ_ПРОЕКТА]
"""

import sys
from pathlib import Path

MOTD = """\
PzhavOS live environment.

The installer starts automatically on tty1.
If it did not, run it manually:
    python /opt/pzhavos-installer/main.py --live

Network:
    Wi-Fi ............ iwctl
    Mobile (WWAN) .... mmcli
    Ethernet / WLAN / WWAN over DHCP should work automatically.

Switch to a console: Ctrl+Alt+F2
"""

ISSUE = "PzhavOS \\r (\\l)\n\n"

OS_RELEASE = """\
NAME="PzhavOS"
PRETTY_NAME="PzhavOS"
ID=pzhavos
ID_LIKE=arch
BUILD_ID=rolling
ANSI_COLOR="38;2;69;136;131"
LOGO=pzhavos
"""

TARGETS = [
    ("motd", MOTD),
    ("issue", ISSUE),
    ("os-release", OS_RELEASE),
]


def find_root(argv):
    if len(argv) > 1:
        return Path(argv[1]).expanduser().resolve()
    for cand in (Path.cwd(), Path.cwd() / "pzhavos", Path.home() / "pzhavos"):
        if (cand / "iso/profile/airootfs/etc").is_dir():
            return cand.resolve()
    return None


def main():
    root = find_root(sys.argv)
    etc = None if root is None else root / "iso/profile/airootfs/etc"
    if etc is None or not etc.is_dir():
        print("ОШИБКА: не найден iso/profile/airootfs/etc.")
        print("Запусти:  python3 patch_v8_livetty.py /путь/к/pzhavos")
        return 1

    print(f"ISO-профиль: {etc}")
    print("─" * 70)

    planned = []
    problems = []

    for name, content in TARGETS:
        path = etc / name
        if path.is_symlink():
            problems.append(f"{name}: это СИМЛИНК ({path.readlink()}) — руками разберись")
            continue
        if path.is_file():
            cur = path.read_text(encoding="utf-8")
            if cur == content:
                print(f"  = {name}: уже такой, пропускаю")
                continue
            print(f"  ~ {name}: перезаписываю (был {len(cur)} б -> станет {len(content)} б)")
        else:
            print(f"  + {name}: создаю")
        planned.append((path, content))

    print("─" * 70)
    if problems:
        print("ОТКАТ. Ни один файл НЕ изменён. Причины:")
        for p in problems:
            print(f"  ! {p}")
        return 2

    if not planned:
        print("Изменений нет — всё уже на месте. OK.")
        return 0

    for path, content in planned:
        if path.is_file():
            bak = path.with_name(path.name + ".v8bak")
            if not bak.exists():
                bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.write_text(content, encoding="utf-8")
        path.chmod(0o644)
        print(f"  ЗАПИСАН: {path}")

    print("─" * 70)
    print("ГОТОВО. Проверка после сборки — в live: cat /etc/issue; cat /etc/os-release")
    return 0


if __name__ == "__main__":
    sys.exit(main())
