#!/usr/bin/env python3
"""Патч 58 — выпиливание zapret2 и v2raya из дистрибутива.

Правит только живые файлы. Каталоги сборки в repo/ и готовые пакеты
удаляются отдельно, руками.

Запуск:
    python3 patch_drop58.py --dry
    python3 patch_drop58.py
"""
import ast
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path.home() / "pzhavos"
DRY = "--dry" in sys.argv
STAMP = time.strftime("%Y%m%d-%H%M%S")

CONFIG_GEN = ["installer/config_gen.py",
              "iso/profile/airootfs/opt/ouvert-installer/config_gen.py"]
PKGBUILD = "pkgbuilds/ouvert-branding/PKGBUILD"
README = "pkgbuilds/ouvert-branding/README-zapret2.txt"

# из строки chown вырезаем только памятку, сам chown на .config остаётся
CHOWN_CUT = re.compile(r'\s*\\"\$h/README-zapret2\.txt\\"')


def fix_config_gen(text):
    out, dropped = [], 0
    for ln in text.splitlines(keepends=True):
        s = ln.strip()
        if "README-zapret2.txt" in ln and "cp /etc/skel" in ln:
            dropped += 1
            continue
        if s in ('"v2raya",', '"zapret2",') or s.startswith('"ipset",'):
            dropped += 1
            continue
        if "chown" in ln and "README-zapret2.txt" in ln:
            ln = CHOWN_CUT.sub("", ln, count=1)
        out.append(ln)
    return "".join(out), dropped


def fix_pkgbuild(text):
    out, dropped = [], 0
    for ln in text.splitlines(keepends=True):
        if "pkgdesc" in ln:
            ln = ln.replace(", памятка zapret2", "")
        elif "zapret2" in ln:
            dropped += 1
            continue
        out.append(ln)
    return "".join(out), dropped


def main():
    targets = [(rel, fix_config_gen) for rel in CONFIG_GEN] + [(PKGBUILD, fix_pkgbuild)]
    missing = [rel for rel, _ in targets if not (ROOT / rel).is_file()]
    if missing:
        sys.exit("НЕТ ФАЙЛОВ, патч не применён:\n  " + "\n  ".join(missing))

    plan = []
    for rel, fixer in targets:
        p = ROOT / rel
        src = p.read_text(encoding="utf-8")
        dst, dropped = fixer(src)
        if dst != src:
            plan.append((rel, p, src, dst, dropped))

    print(f"{'ФАЙЛ':62} СТРОК-  БЫЛО→СТАЛО")
    for rel, _, src, dst, dropped in plan:
        print(f"{rel:62} {dropped:5}  {len(src.encode())}→{len(dst.encode())}")
    if not plan:
        print("Изменений нет — уже применено.")
    r = ROOT / README
    print(f"\nПамятка {README}: {'на месте, будет удалена' if r.exists() else 'уже удалена'}")

    if DRY:
        print("\nКОНТРОЛЬНЫЙ ПРОГОН: ничего не записано.")
        return

    for rel, p, src, dst, _ in plan:
        shutil.copy2(p, p.with_name(p.name + f".p58bak-{STAMP}"))
        p.write_text(dst, encoding="utf-8")
        if p.suffix == ".py":
            ast.parse(dst)
    print(f"\nЗаписано файлов: {len(plan)}. Бэкапы: *.p58bak-{STAMP}")

    if r.exists():
        res = subprocess.run(["git", "-C", str(ROOT), "rm", "-q", "--", README],
                             capture_output=True, text=True)
        if res.returncode:
            r.unlink()
            print("памятка удалена (вне git)")
        else:
            print("git rm: " + README)

    left = subprocess.run(
        ["grep", "-rIin", "-e", "zapret", "-e", "v2ray",
         str(ROOT / "installer"), str(ROOT / "iso"), str(ROOT / "pkgbuilds"),
         "--exclude=*bak*", "--exclude=*namcap.log", "--exclude-dir=pkg", "--exclude-dir=src"],
        capture_output=True, text=True).stdout
    keep = [ln for ln in left.splitlines() if "/patch_" not in ln]
    print("\nОстались упоминания в живых файлах:")
    print("\n".join("  " + x for x in keep) or "  нет")


if __name__ == "__main__":
    main()
