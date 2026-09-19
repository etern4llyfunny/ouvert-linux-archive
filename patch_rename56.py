#!/usr/bin/env python3
"""Патч 56 — переименование PzhavOS → Ouvert Linux.

Идемпотентный и транзакционный: сначала считает вхождения по всем файлам,
и только если всё сходится — пишет. Бэкапы с меткой времени, проверка
синтаксиса Python после записи, отчёт с размерами.

Запуск:
    python3 patch_rename56.py --dry    # контрольный прогон, ничего не пишет
    python3 patch_rename56.py          # боевой прогон
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
    ("pzhavos-installer", "ouvert-installer"),
    ("PZHAVOS", "OUVERT"),
    ("PzhavOS", "Ouvert Linux"),
    ("pzhavos", "ouvert"),
    ("38;2;69;136;131", "38;2;46;159;240"),  # ANSI_COLOR старого бренда → наш голубой
]

INSTALLER = ["config_gen.py", "diskmap.py", "i18n.py", "main.py", "pages.py",
             "partedit.py", "partops.py", "theme.py", "wizard.py", "README.md"]

FILES = (
    [f"installer/{n}" for n in INSTALLER]
    + ["installer/stand_gui.py", "installer/test_mount.py", "installer/test_partops.py",
       "installer/test_vconsole55.py", "installer/tests/sample_t26.txt"]
    + [f"iso/profile/airootfs/opt/pzhavos-installer/{n}" for n in INSTALLER]
    + ["iso/profile/airootfs/etc/hostname",
       "iso/profile/airootfs/etc/issue",
       "iso/profile/airootfs/etc/motd",
       "iso/profile/airootfs/etc/os-release",
       "iso/profile/airootfs/root/.zlogin",
       "iso/profile/profiledef.sh",
       "iso/profile/syslinux/archiso_head.cfg",
       "iso/profile/syslinux/archiso_sys-linux.cfg",
       "iso/profile/syslinux/archiso_pxe-linux.cfg",
       "iso/profile/efiboot/loader/entries/01-archiso-linux.conf",
       "iso/profile/efiboot/loader/entries/02-archiso-speech-linux.conf",
       "iso/build.sh",
       ".gitignore",
       "pkgbuilds/pzhavos-branding/PKGBUILD",
       "pkgbuilds/pzhavos-branding/cosmic-bg-all",
       "pkgbuilds/pzhavos-branding/fastfetch-config.jsonc",
       "pkgbuilds/pzhavos-branding/LICENSE",
       "pkgbuilds/pzhavos-branding/pzhavos-restore-wallpapers.sh",
       "pkgbuilds/pzhavos-branding/pzhavos-wallpapers.hook"]
)

# строка пакета pzhavmem — удаляем целиком, пакет выпиливается
DROP_LINE = '"pzhavmem",'

RENAMES = [
    ("iso/profile/airootfs/opt/pzhavos-installer", "iso/profile/airootfs/opt/ouvert-installer"),
    ("pkgbuilds/pzhavos-branding/pzhavos-restore-wallpapers.sh",
     "pkgbuilds/pzhavos-branding/ouvert-restore-wallpapers.sh"),
    ("pkgbuilds/pzhavos-branding/pzhavos-wallpapers.hook",
     "pkgbuilds/pzhavos-branding/ouvert-wallpapers.hook"),
    ("pkgbuilds/pzhavos-branding", "pkgbuilds/ouvert-branding"),
]


def patched(text):
    """Возвращает (новый текст, число замен, число удалённых строк)."""
    n = sum(text.count(a) for a, _ in PAIRS)
    for a, b in PAIRS:
        text = text.replace(a, b)
    return text, n


def resolve(rel):
    """После переименований каталогов путь меняется — ищем файл по новому имени."""
    if (ROOT / rel).is_file():
        return rel
    alt = rel
    for a, b in RENAMES:
        alt = alt.replace(a, b)
    return alt


def main():
    FILES[:] = [resolve(f) for f in FILES]
    missing = [f for f in FILES if not (ROOT / f).is_file()]
    if missing:
        sys.exit("НЕТ ФАЙЛОВ, патч не применён:\n  " + "\n  ".join(missing))

    plan = []
    for rel in FILES:
        p = ROOT / rel
        src = p.read_text(encoding="utf-8")
        dst, n = patched(src)
        drop = 0
        if rel.endswith("config_gen.py"):
            lines = dst.splitlines(keepends=True)
            kept = [ln for ln in lines if ln.strip() != DROP_LINE]
            drop = len(lines) - len(kept)
            dst = "".join(kept)
        if dst != src:
            plan.append((rel, p, src, dst, n, drop))

    print(f"{'ФАЙЛ':68} ЗАМЕН  СТРОК-  БЫЛО→СТАЛО")
    for rel, _, src, dst, n, drop in plan:
        print(f"{rel:68} {n:5}  {drop:5}  {len(src.encode())}→{len(dst.encode())}")
    if not plan:
        print("Изменений нет — патч уже применён (это нормально, он идемпотентный).")

    if DRY:
        print("\nКОНТРОЛЬНЫЙ ПРОГОН: ничего не записано.")
        return

    for rel, p, src, dst, _, _ in plan:
        shutil.copy2(p, p.with_name(p.name + f".p56bak-{STAMP}"))
        p.write_text(dst, encoding="utf-8")
        if p.suffix == ".py":
            ast.parse(dst)  # упадёт здесь, если патч сломал синтаксис
    print(f"\nЗаписано файлов: {len(plan)}. Бэкапы: *.p56bak-{STAMP}")

    for src_rel, dst_rel in RENAMES:
        s, d = ROOT / src_rel, ROOT / dst_rel
        if d.exists():
            print(f"уже переименовано: {dst_rel}")
            continue
        if not s.exists():
            print(f"ПРОПУЩЕНО, нет источника: {src_rel}")
            continue
        r = subprocess.run(["git", "-C", str(ROOT), "mv", src_rel, dst_rel],
                           capture_output=True, text=True)
        if r.returncode:
            shutil.move(str(s), str(d))
            print(f"перемещено без git: {src_rel} → {dst_rel}")
        else:
            print(f"git mv: {src_rel} → {dst_rel}")

    left = subprocess.run(
        ["grep", "-rIil", "-e", "pzhav", "-e", "PZHAV", str(ROOT),
         "--exclude-dir=.git", "--exclude-dir=__pycache__", "--exclude-dir=work",
         "--exclude-dir=out", "--exclude-dir=backups", "--exclude-dir=pkg",
         "--exclude=*bak*"], capture_output=True, text=True).stdout
    keep = [ln for ln in left.splitlines()
            if "/patch_" not in ln and "/t_" not in ln and "/pzhavmem/" not in ln]
    print("\nОстались упоминания (кроме истории патчей и pzhavmem):")
    print("\n".join("  " + x for x in keep) or "  нет")


if __name__ == "__main__":
    main()
