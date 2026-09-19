#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PzhavOS — патч v8.

ЧТО ДЕЛАЕТ (installer/ — мастер, build.sh сам rsync'ает его в ISO-профиль):

  1) config_gen.py: BUG 21 — раскладка на Cinnamon.
     В /etc/dconf/db/local.d/02-pzhavos-keyboard добавляются ДВЕ группы
     форкнутых схем Cinnamon:
        [org/cinnamon/desktop/input-sources]   sources=us,ru
        [org/cinnamon/desktop/keybindings/wm]  switch-input-source=Alt+Shift
     xkb-options для Cinnamon НЕ пишется сознательно: переключает кейбиндинг
     Muffin, xkb-опция сверху дала бы двойное срабатывание.
     Доказано вживую на t20 (27.07.2026): sources из системной базы доехали
     после `gsettings reset`, Alt+Shift дал «фис abc фис».

  2) config_gen.py: системный слой xkb — /etc/environment
        XKB_DEFAULT_LAYOUT=us,ru
        XKB_DEFAULT_OPTIONS=grp:alt_shift_toggle
     Для «голых» wayland-композиторов (niri, sway, labwc, hyprland): они
     читают libxkbcommon, а не dconf/kxkbrc. GNOME/KDE/Cinnamon игнорируют.
     Строки переписываются идемпотентно (sed -i + append).

  3) desktops.py: порядок списка DE ->
        Cinnamon -> GNOME -> XFCE -> COSMIC -> KDE Plasma -> остальные.

  4) VERSION: v7 -> v8 (и стухший маркер в шапке v5 -> v8).

СВОЙСТВА: транзакционный (проверяет ВСЕ якоря до записи хоть одного файла),
идемпотентный (повторный запуск = 0 изменений), компилирует результат в
памяти до записи на диск.

ЗАПУСК:  python3 patch_v8_cinnamon.py [КОРЕНЬ_ПРОЕКТА]
"""

import sys
from pathlib import Path

# ─────────────────────────── config_gen.py ───────────────────────────

CG_OLD_KB = r'''            "switch-input-source-backward=['<Shift>Alt_L']\n"
            "KBDEOF\n"
            "dconf update || true\n"
        )
'''

CG_NEW_KB = r'''            "switch-input-source-backward=['<Shift>Alt_L']\n"
            "\n"
            # Cinnamon форкнул гномовские схемы. Гномовские он ЧИТАЕТ, но
            # csd-keyboard применяет ИМЕННО свои (доказано на t20 27.07.26).
            # xkb-options здесь НЕ пишем: переключает кейбиндинг Muffin,
            # xkb-опция сверху дала бы двойное срабатывание Alt+Shift.
            "[org/cinnamon/desktop/input-sources]\n"
            f"sources=[{srcs}]\n"
            "\n"
            "[org/cinnamon/desktop/keybindings/wm]\n"
            "switch-input-source=['<Alt>Shift_L']\n"
            "switch-input-source-backward=['<Shift>Alt_L']\n"
            "KBDEOF\n"
            "dconf update || true\n"
            # Системный слой xkb для «голых» wayland-композиторов
            # (niri, sway, labwc, hyprland): они читают libxkbcommon и знать
            # не знают ни про dconf, ни про kxkbrc. GNOME/KDE/Cinnamon эти
            # переменные игнорируют -> двойного переключения не будет.
            "touch /etc/environment\n"
            "sed -i '/^XKB_DEFAULT_LAYOUT=/d;/^XKB_DEFAULT_OPTIONS=/d' /etc/environment || true\n"
            f"printf 'XKB_DEFAULT_LAYOUT={layout}\\nXKB_DEFAULT_OPTIONS={opts}\\n' >> /etc/environment\n"
        )
'''

CG_OLD_VER = 'VERSION = "v7"\n'
CG_NEW_VER = 'VERSION = "v8"\n'

CG_OLD_HDR = 'ВЕРСИЯ: v5 (маркер для проверки свежести: grep VERSION config_gen.py)\n'
CG_NEW_HDR = 'ВЕРСИЯ: v8 (маркер для проверки свежести: grep VERSION config_gen.py)\n'

# ──────────────────────────── desktops.py ────────────────────────────

DE_OLD = '''DESKTOP_ENVIRONMENTS = [
    ("KDE Plasma", "KDE Plasma", "plasma-login-manager"),
    ("GNOME", "GNOME", "gdm"),
    ("Cinnamon", "Cinnamon", "lightdm-gtk-greeter"),
    ("XFCE", "Xfce4", "lightdm-gtk-greeter"),
    ("MATE", "Mate", "lightdm-gtk-greeter"),
    ("Budgie", "Budgie", "lightdm-slick-greeter"),
    ("LXQt", "Lxqt", "sddm"),
    ("Deepin", "Deepin", "lightdm-gtk-greeter"),
    ("Enlightenment", "Enlightenment", "lightdm-gtk-greeter"),
    ("COSMIC", "Cosmic", "cosmic-greeter"),
]
'''

DE_NEW = '''DESKTOP_ENVIRONMENTS = [
    ("Cinnamon", "Cinnamon", "lightdm-gtk-greeter"),
    ("GNOME", "GNOME", "gdm"),
    ("XFCE", "Xfce4", "lightdm-gtk-greeter"),
    ("COSMIC", "Cosmic", "cosmic-greeter"),
    ("KDE Plasma", "KDE Plasma", "plasma-login-manager"),
    ("MATE", "Mate", "lightdm-gtk-greeter"),
    ("Budgie", "Budgie", "lightdm-slick-greeter"),
    ("LXQt", "Lxqt", "sddm"),
    ("Deepin", "Deepin", "lightdm-gtk-greeter"),
    ("Enlightenment", "Enlightenment", "lightdm-gtk-greeter"),
]
'''

EDITS = {
    "installer/config_gen.py": [
        ("блок раскладки (Cinnamon + /etc/environment)", CG_OLD_KB, CG_NEW_KB),
        ("VERSION v7 -> v8", CG_OLD_VER, CG_NEW_VER),
        ("маркер в шапке v5 -> v8", CG_OLD_HDR, CG_NEW_HDR),
    ],
    "installer/desktops.py": [
        ("порядок DE", DE_OLD, DE_NEW),
    ],
}


def find_root(argv):
    if len(argv) > 1:
        return Path(argv[1]).expanduser().resolve()
    for cand in (Path.cwd(), Path.cwd() / "pzhavos", Path.home() / "pzhavos"):
        if (cand / "installer" / "config_gen.py").is_file():
            return cand.resolve()
    return None


def main():
    root = find_root(sys.argv)
    if root is None or not (root / "installer" / "config_gen.py").is_file():
        print("ОШИБКА: не найден installer/config_gen.py.")
        print("Запусти:  python3 patch_v8_cinnamon.py /путь/к/pzhavos")
        return 1

    print(f"Корень проекта: {root}")
    print("─" * 70)

    planned = {}   # path -> new text
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
                    f"{rel}: якорь «{name}» найден {n} раз (нужно ровно 1)")
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
        _report_iso_copy(root)
        return 0

    for path, text in planned.items():
        bak = path.with_suffix(path.suffix + ".v8bak")
        if not bak.exists():
            bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.write_text(text, encoding="utf-8")
        print(f"  ЗАПИСАН: {path}  (бэкап: {bak.name})")

    print("─" * 70)
    print("ГОТОВО.")
    _report_iso_copy(root)
    return 0


def _report_iso_copy(root):
    """ISO-копия НЕ патчится: build.sh делает rsync installer/ -> профиль.
    Просто показываем её версию, чтобы видеть дрейф."""
    iso = root / "iso/profile/airootfs/opt/pzhavos-installer/config_gen.py"
    print("─" * 70)
    if not iso.is_file():
        print("ISO-копия: не найдена (норма, если профиль ещё не синхронизирован).")
        return
    for line in iso.read_text(encoding="utf-8").splitlines():
        if line.startswith("VERSION = "):
            print(f"ISO-копия сейчас: {line.strip()}  <- перетрётся при build.sh")
            return
    print("ISO-копия: строка VERSION не найдена.")


if __name__ == "__main__":
    sys.exit(main())
