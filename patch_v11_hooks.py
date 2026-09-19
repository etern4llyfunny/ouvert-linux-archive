#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_v11_hooks.py — PzhavOS, этап 3.

ЧТО ДЕЛАЕТ:
  1. Кладёт в pkgbuilds/pzhavos-branding/ два новых файла:
       pzhavos-wallpapers.hook          (pacman-хук, триггер ПО ПУТЯМ)
       pzhavos-restore-wallpapers.sh    (скрипт восстановления обоев)
  2. Правит PKGBUILD: pkgrel 3 -> 4, +2 источника, +2 sha256sums,
     +2 строки install в package().

СВОЙСТВА:
  - ТРАНЗАКЦИОННЫЙ: все якоря проверяются ДО записи хоть одного байта.
  - ИДЕМПОТЕНТНЫЙ: повторный запуск = 0 изменений.
  - С БЭКАПОМ: PKGBUILD.v11bak рядом.
"""

import os
import re
import shutil
import sys

BASE = os.path.expanduser("~/pzhavos/pkgbuilds/pzhavos-branding")
PKGBUILD = os.path.join(BASE, "PKGBUILD")

HOOK_NAME = "pzhavos-wallpapers.hook"
SCRIPT_NAME = "pzhavos-restore-wallpapers.sh"

HOOK_TEXT = """[Trigger]
Type = Path
Operation = Install
Operation = Upgrade
Target = usr/share/backgrounds/xfce/*
Target = usr/share/wallpapers/Next/contents/images/*
Target = usr/share/wallpapers/Next/contents/images_dark/*

[Action]
Description = Restoring PzhavOS wallpapers...
When = PostTransaction
Exec = /usr/share/pzhavos/restore-wallpapers.sh
"""

SCRIPT_TEXT = r"""#!/bin/bash
# PzhavOS: восстановление обоев после обновления пакетов, которые их перетирают
# (xfdesktop, plasma-workspace-wallpapers и любые их наследники).
# Вызывается хуком /usr/share/libalpm/hooks/pzhavos-wallpapers.hook.
# Повторяет логику установщика (config_gen.py, блок обоев).
#
# ПРИНЦИП: никогда не валить транзакцию pacman. Нет set -e, всегда exit 0.

SRC_XFCE=/usr/share/wallpapers/PzhavOS/pzhav.png
SRC_KDE=/usr/share/wallpapers/PzhavOS/pzhav-kde.png

# XFCE: подмена дефолтных фонов xfdesktop. GdkPixbuf определяет формат по
# содержимому, поэтому PNG под именем *.svg рендерится нормально.
if [ -f "$SRC_XFCE" ] && [ -d /usr/share/backgrounds/xfce ]; then
  for f in /usr/share/backgrounds/xfce/*; do
    [ -f "$f" ] || continue
    cmp -s "$SRC_XFCE" "$f" || cp -f "$SRC_XFCE" "$f" || true
  done
fi

# KDE Plasma: подмена содержимого дефолтного набора Next, все разрешения
# + images_dark.
if [ -f "$SRC_KDE" ] && [ -d /usr/share/wallpapers/Next/contents ]; then
  for f in /usr/share/wallpapers/Next/contents/images/*.png \
           /usr/share/wallpapers/Next/contents/images_dark/*.png; do
    [ -f "$f" ] || continue
    cmp -s "$SRC_KDE" "$f" || cp -f "$SRC_KDE" "$f" || true
  done
fi

exit 0
"""

# --- якоря PKGBUILD -----------------------------------------------------------

A_PKGREL_OLD = "pkgrel=3\n"
A_PKGREL_NEW = "pkgrel=4\n"

A_SRC_OLD = "        'README-zapret2.txt')\n"
A_SRC_NEW = ("        'README-zapret2.txt'\n"
             "        '" + HOOK_NAME + "'\n"
             "        '" + SCRIPT_NAME + "')\n")

A_SUM_OLD = "            'SKIP')\n"
A_SUM_NEW = ("            'SKIP'\n"
             "            'SKIP'\n"
             "            'SKIP')\n")

A_INST_OLD = ('    install -Dm644 "$srcdir/README-zapret2.txt" '
              '"$pkgdir/etc/skel/README-zapret2.txt"\n')
A_INST_NEW = A_INST_OLD + (
    "    # pacman-хук: обновление xfdesktop / plasma-workspace-wallpapers\n"
    "    # затирает наши обои штатными. Триггер ПО ПУТЯМ, а не по имени\n"
    "    # пакета: имена в Arch переезжают, путь — нет.\n"
    '    install -Dm644 "$srcdir/' + HOOK_NAME + '" '
    '"$pkgdir/usr/share/libalpm/hooks/' + HOOK_NAME + '"\n'
    '    install -Dm755 "$srcdir/' + SCRIPT_NAME + '" '
    '"$pkgdir/usr/share/pzhavos/restore-wallpapers.sh"\n'
)


def die(msg):
    print("ОТМЕНА: " + msg)
    sys.exit(1)


def main():
    if not os.path.isdir(BASE):
        die("нет каталога " + BASE)
    if not os.path.isfile(PKGBUILD):
        die("нет файла " + PKGBUILD)

    with open(PKGBUILD, "r", encoding="utf-8") as f:
        text = f.read()

    # --- идемпотентность ---
    already = HOOK_NAME in text
    if already:
        print("PKGBUILD уже содержит хук — правки не требуются.")

    # --- ФАЗА 1: проверка ВСЕХ якорей до любой записи ---
    if not already:
        checks = [
            ("pkgrel=3", A_PKGREL_OLD, 1),
            ("закрытие массива source", A_SRC_OLD, 1),
            ("закрытие массива sha256sums", A_SUM_OLD, 1),
            ("install README-zapret2", A_INST_OLD, 1),
        ]
        for name, anchor, want in checks:
            got = text.count(anchor)
            if got != want:
                die("якорь «%s» найден %d раз(а), ожидалось %d. "
                    "Файл изменился — патч не применён." % (name, got, want))
        print("Якоря PKGBUILD: 4/4 — OK.")

        new_text = text
        new_text = new_text.replace(A_PKGREL_OLD, A_PKGREL_NEW, 1)
        new_text = new_text.replace(A_SRC_OLD, A_SRC_NEW, 1)
        new_text = new_text.replace(A_SUM_OLD, A_SUM_NEW, 1)
        new_text = new_text.replace(A_INST_OLD, A_INST_NEW, 1)

        # sanity: массивы должны сойтись по числу элементов
        m_src = re.search(r"^source=\((.*?)\)\s*$", new_text,
                          re.S | re.M)
        m_sum = re.search(r"^sha256sums=\((.*?)\)\s*$", new_text,
                          re.S | re.M)
        if not m_src or not m_sum:
            die("не разобрал массивы source/sha256sums после правки.")
        n_src = len(re.findall(r"'", m_src.group(1))) // 2
        n_sum = len(re.findall(r"'", m_sum.group(1))) // 2
        if n_src != n_sum:
            die("рассинхрон: source=%d элементов, sha256sums=%d." %
                (n_src, n_sum))
        print("Сверка массивов: source=%d, sha256sums=%d — OK." %
              (n_src, n_sum))
    else:
        new_text = text

    # --- ФАЗА 2: запись ---
    hook_path = os.path.join(BASE, HOOK_NAME)
    script_path = os.path.join(BASE, SCRIPT_NAME)

    changed = []

    def write_if_diff(path, content, mode):
        old = None
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                old = fh.read()
        if old == content:
            os.chmod(path, mode)
            return False
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.chmod(path, mode)
        return True

    if write_if_diff(hook_path, HOOK_TEXT, 0o644):
        changed.append(HOOK_NAME)
    if write_if_diff(script_path, SCRIPT_TEXT, 0o755):
        changed.append(SCRIPT_NAME)

    if new_text != text:
        shutil.copy2(PKGBUILD, PKGBUILD + ".v11bak")
        with open(PKGBUILD, "w", encoding="utf-8") as f:
            f.write(new_text)
        changed.append("PKGBUILD (бэкап: PKGBUILD.v11bak)")

    print("")
    if changed:
        print("ИЗМЕНЕНО:")
        for c in changed:
            print("  + " + c)
    else:
        print("ИЗМЕНЕНИЙ НЕТ (всё уже на месте).")

    print("")
    print("ДАЛЬШЕ ВРУЧНУЮ:")
    print("  1. cd ~/pzhavos/pkgbuilds/pzhavos-branding && extra-x86_64-build")
    print("  2. repo-add в ~/pzhavos/repo/x86_64/")
    print("  3. rsync репо в ISO-профиль")


if __name__ == "__main__":
    main()
