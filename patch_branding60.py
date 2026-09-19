#!/usr/bin/env python3
"""Патч 60 — пакет ouvert-branding под новый набор обоев.

1. PKGBUILD: убраны обои ouvert-walp2/walp3 (запас, которого больше нет),
   ouvert-kde.png (KDE из дистрибутива выкинут) и ouvert-cosmic.png
   (COSMIC теперь берёт тот же ouvert.png).
2. PKGBUILD: license='LicenseRef-Ouvert Linux' → 'LicenseRef-Ouvert'
   (пробел в идентификаторе лицензии — последствие Патча 56, namcap ругается).
3. PKGBUILD: блок sha256sums пересчитан по числу источников — сейчас их 16,
   а сумм 17 (хвост от выпиленной памятки zapret), makepkg на этом падает.
4. cosmic-bg-all: путь обоев переведён на ouvert.png.
5. ouvert-restore-wallpapers.sh: выброшен блок восстановления обоев KDE.

Запуск:
    python3 patch_branding60.py --dry
    python3 patch_branding60.py
"""
import re
import shutil
import sys
import time
from pathlib import Path

DIR = Path.home() / "pzhavos" / "pkgbuilds" / "ouvert-branding"
DRY = "--dry" in sys.argv
STAMP = time.strftime("%Y%m%d-%H%M%S")

DROP_SOURCES = {"'ouvert-walp2.png'", "'ouvert-walp3.png'",
                "'ouvert-kde.png'", "'ouvert-cosmic.png'"}
DROP_IN_PACKAGE = ("ouvert-walp2.png", "ouvert-walp3.png",
                   "ouvert-kde.png", "ouvert-cosmic.png",
                   "# Bug 47 cosmic: обои COSMIC")

KDE_BLOCK = '''
# KDE Plasma: подмена содержимого дефолтного набора Next, все разрешения
# + images_dark.
if [ -f "$SRC_KDE" ] && [ -d /usr/share/wallpapers/Next/contents ]; then
  for f in /usr/share/wallpapers/Next/contents/images/*.png \\
           /usr/share/wallpapers/Next/contents/images_dark/*.png; do
    [ -f "$f" ] || continue
    cmp -s "$SRC_KDE" "$f" || cp -f "$SRC_KDE" "$f" || true
  done
fi
'''
KDE_SRC_LINE = 'SRC_KDE=/usr/share/wallpapers/Ouvert/ouvert-kde.png\n'

COMMENT_OLD = "    # Обои (все 4: ouvert — дефолт, walp1-3 — запас, лежат в системе)\n"
COMMENT_NEW = "    # Обои: ouvert — дефолт (угол), ouvert-walp — запасная (лок-ап)\n"


def fix_pkgbuild(text):
    out = []
    for ln in text.splitlines(keepends=True):
        s = ln.strip()
        if s in DROP_SOURCES:                      # строки source=()
            continue
        if any(d in ln for d in DROP_IN_PACKAGE):  # install-строки и комментарий
            continue
        out.append(ln)
    text = "".join(out).replace(COMMENT_OLD, COMMENT_NEW)
    text = text.replace("license=('LicenseRef-Ouvert Linux')", "license=('LicenseRef-Ouvert')")

    # sha256sums строго по числу источников
    src = re.search(r"source=\((.*?)\)\n", text, re.S)
    n = len(re.findall(r"'[^']+'", src.group(1)))
    sums = "sha256sums=(" + ("\n" + " " * 12).join(["'SKIP'"] * n) + ")\n"
    text = re.sub(r"sha256sums=\(.*?\)\n", sums, text, count=1, flags=re.S)
    return text, n


def main():
    targets = {
        "PKGBUILD": None,
        "cosmic-bg-all": lambda t: t.replace("ouvert-cosmic.png", "ouvert.png"),
        "ouvert-restore-wallpapers.sh": lambda t: t.replace(KDE_BLOCK, "").replace(KDE_SRC_LINE, ""),
    }
    plan = []
    for name, fixer in targets.items():
        p = DIR / name
        if not p.is_file():
            sys.exit(f"НЕТ ФАЙЛА: {p}")
        src = p.read_text(encoding="utf-8")
        if name == "PKGBUILD":
            dst, n = fix_pkgbuild(src)
            print(f"источников в PKGBUILD после правки: {n}, столько же будет sha256sums")
        else:
            dst = fixer(src)
        if dst != src:
            plan.append((name, p, src, dst))

    print(f"\n{'ФАЙЛ':34} БЫЛО→СТАЛО")
    for name, _, src, dst in plan:
        print(f"{name:34} {len(src.encode())}→{len(dst.encode())}")
    if not plan:
        print("Изменений нет — уже применено.")

    gone = [f for f in ("ouvert-walp2.png", "ouvert-walp3.png",
                        "ouvert-kde.png", "ouvert-cosmic.png") if (DIR / f).exists()]
    print("\nЛишние картинки на диске (удалить через git rm вручную): "
          + (", ".join(gone) if gone else "нет"))

    if DRY:
        print("\nКОНТРОЛЬНЫЙ ПРОГОН: ничего не записано.")
        return

    for name, p, _, dst in plan:
        shutil.copy2(p, p.with_name(p.name + f".p60bak-{STAMP}"))
        p.write_text(dst, encoding="utf-8")
    print(f"\nЗаписано файлов: {len(plan)}. Бэкапы: *.p60bak-{STAMP}")


if __name__ == "__main__":
    main()
