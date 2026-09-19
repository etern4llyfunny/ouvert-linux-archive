#!/usr/bin/env python3
"""Патч 57 — добивка после Патча 56.

Чинит три вещи:
  1. путь с пробелом /usr/share/wallpapers/Ouvert Linux/ → .../Ouvert/
  2. имена картинок: pzhav*.png и Ouvert Linuxwalp*.png → ouvert*.png
  3. внутренние имена стенда: PZHAV_* → OUVERT_*, pzhav- → ouvert-

Запуск:
    python3 patch_rename57.py --dry    # контрольный прогон
    python3 patch_rename57.py          # боевой прогон
"""
import ast
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path.home() / "pzhavos"
DRY = "--dry" in sys.argv
STAMP = time.strftime("%Y%m%d-%H%M%S")

# порядок важен: от длинного к короткому
PAIRS = [
    ("wallpapers/Ouvert Linux", "wallpapers/Ouvert"),
    ("Ouvert Linuxwalp", "ouvert-walp"),
    ("PzhavOSwalp", "ouvert-walp"),
    ("pzhavos-logo", "ouvert-logo"),
    ("pzhav-kde", "ouvert-kde"),
    ("pzhav-cosmic", "ouvert-cosmic"),
    ("pzhav.png", "ouvert.png"),
    ("PZHAV_", "OUVERT_"),
    ("pzhav-", "ouvert-"),
]

FILES = [
    "installer/config_gen.py",
    "installer/diskmap.py",
    "installer/partedit.py",
    "installer/partops.py",
    "installer/stand_gui.py",
    "installer/test_mount.py",
    "installer/test_partops.py",
    "installer/test_vconsole55.py",
    "installer/tests/sample_t26.txt",
    "iso/profile/airootfs/opt/ouvert-installer/config_gen.py",
    "iso/profile/airootfs/opt/ouvert-installer/diskmap.py",
    "iso/profile/airootfs/opt/ouvert-installer/partedit.py",
    "iso/profile/airootfs/opt/ouvert-installer/partops.py",
    "pkgbuilds/ouvert-branding/PKGBUILD",
    "pkgbuilds/ouvert-branding/cosmic-bg-all",
    "pkgbuilds/ouvert-branding/cosmic-bg-backgrounds",
    "pkgbuilds/ouvert-branding/fastfetch-config.jsonc",
    "pkgbuilds/ouvert-branding/ouvert-restore-wallpapers.sh",
    "pkgbuilds/ouvert-branding/ouvert-wallpapers.hook",
]

B = "pkgbuilds/ouvert-branding/"
RENAMES = [
    (B + "pzhav.png", B + "ouvert.png"),
    (B + "pzhav-kde.png", B + "ouvert-kde.png"),
    (B + "pzhav-cosmic.png", B + "ouvert-cosmic.png"),
    (B + "PzhavOSwalp.png", B + "ouvert-walp.png"),
    (B + "PzhavOSwalp2.png", B + "ouvert-walp2.png"),
    (B + "PzhavOSwalp3.png", B + "ouvert-walp3.png"),
    (B + "pzhavos-logo.png", B + "ouvert-logo.png"),
]


def main():
    missing = [f for f in FILES if not (ROOT / f).is_file()]
    if missing:
        sys.exit("НЕТ ФАЙЛОВ, патч не применён:\n  " + "\n  ".join(missing))

    plan = []
    for rel in FILES:
        p = ROOT / rel
        src = p.read_text(encoding="utf-8")
        dst = src
        n = sum(src.count(a) for a, _ in PAIRS)
        for a, b in PAIRS:
            dst = dst.replace(a, b)
        if dst != src:
            plan.append((rel, p, src, dst, n))

    print(f"{'ФАЙЛ':62} ЗАМЕН  БЫЛО→СТАЛО")
    for rel, _, src, dst, n in plan:
        print(f"{rel:62} {n:5}  {len(src.encode())}→{len(dst.encode())}")
    if not plan:
        print("Изменений в текстах нет — уже применено.")

    print("\nПЕРЕИМЕНОВАНИЯ:")
    for s_rel, d_rel in RENAMES:
        s, d = ROOT / s_rel, ROOT / d_rel
        state = "готово" if d.exists() else ("есть" if s.exists() else "НЕТ ИСТОЧНИКА")
        print(f"  {s_rel.split('/')[-1]:24} → {d_rel.split('/')[-1]:24} {state}")

    if DRY:
        print("\nКОНТРОЛЬНЫЙ ПРОГОН: ничего не записано.")
        return

    for rel, p, src, dst, _ in plan:
        shutil.copy2(p, p.with_name(p.name + f".p57bak-{STAMP}"))
        p.write_text(dst, encoding="utf-8")
        if p.suffix == ".py":
            ast.parse(dst)
    print(f"\nЗаписано файлов: {len(plan)}. Бэкапы: *.p57bak-{STAMP}")

    for s_rel, d_rel in RENAMES:
        s, d = ROOT / s_rel, ROOT / d_rel
        if d.exists() or not s.exists():
            continue
        r = subprocess.run(["git", "-C", str(ROOT), "mv", s_rel, d_rel],
                           capture_output=True, text=True)
        if r.returncode:
            shutil.move(str(s), str(d))
            print(f"перемещено без git: {s_rel} → {d_rel}")
        else:
            print(f"git mv: {s_rel} → {d_rel}")

    left = subprocess.run(
        ["grep", "-rIil", "pzhav", str(ROOT), "--exclude-dir=.git", "--exclude-dir=__pycache__",
         "--exclude-dir=work", "--exclude-dir=out", "--exclude-dir=backups", "--exclude-dir=pkg",
         "--exclude-dir=src", "--exclude=*bak*", "--exclude=*namcap.log", "--exclude=*package.log"],
        capture_output=True, text=True).stdout
    keep = [ln for ln in left.splitlines() if "/patch_" not in ln and "/t_" not in ln]
    print("\nОстались упоминания (кроме истории патчей):")
    print("\n".join("  " + x for x in keep) or "  нет")


if __name__ == "__main__":
    main()
