"""Контрольный прогон патча 55 (vconsole как нижний слой раскладки).

★ Правило 13.36: проверки строятся по СГЕНЕРИРОВАННОМУ ВЫВОДУ
  build_custom_commands(), а не по тексту исходника — комментарии
  содержат те же слова, что и команды, и count() их считает.

Запуск:  python test_vconsole55.py     (код 0 = всё прошло)
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import config_gen

ok = 0
fail = 0


def check(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {name}")
    else:
        fail += 1
        print(f"  FAIL {name} {extra}")


def gen(kb):
    return "".join(config_gen.build_custom_commands({"kb": kb}))


print("=== 1. us_ru: новый слой vconsole ===")
s = gen("us_ru")

check("1.1 localectl set-x11-keymap УБРАН",
      "localectl set-x11-keymap" not in s)
check("1.2 запись в /etc/vconsole.conf есть",
      "/etc/vconsole.conf <<'VCEOF'" in s)
check("1.3 чистка старых строк перед записью",
      "/^XKBLAYOUT=/d" in s and "/^KEYMAP=/d" in s)
check("1.4 XKBLAYOUT=us,ru", "\nXKBLAYOUT=us,ru\n" in s)
check("1.5 XKBMODEL=pc105+inet", "\nXKBMODEL=pc105+inet\n" in s)
check("1.6 XKBVARIANT=,", "\nXKBVARIANT=,\n" in s)
check("1.7 XKBOPTIONS=grp:alt_shift_toggle",
      "\nXKBOPTIONS=grp:alt_shift_toggle\n" in s)
check("1.8 KEYMAP=us (Bug 53: логин в TTY латиницей)",
      "\nKEYMAP=us\n" in s)
check("1.9 vconsole пишется ровно один раз",
      s.count("VCEOF") == 2, f"VCEOF={s.count('VCEOF')}")

print("=== 2. us_ru: слой Xorg (00-keyboard.conf) ===")
check("2.1 00-keyboard.conf пишется",
      "/etc/X11/xorg.conf.d/00-keyboard.conf <<'XORGEOF'" in s)
check("2.2 XkbLayout в нём наш",
      '"XkbLayout" "us,ru"' in s)
check("2.3 XkbOptions в нём наш",
      '"XkbOptions" "grp:alt_shift_toggle"' in s)
check("2.4 mkdir каталога xorg.conf.d",
      "mkdir -p /etc/X11/xorg.conf.d" in s)

print("=== 3. us_ru: СТАРЫЕ слои не тронуты ===")
check("3.1 kxkbrc (KDE) жив", "/etc/skel/.config/kxkbrc <<'KXKBEOF'" in s)
check("3.2 LayoutList=us,ru", "LayoutList=us,ru" in s)
check("3.3 dconf (GNOME/Cinnamon) жив",
      "/etc/dconf/db/local.d/02-ouvert-keyboard <<'KBDEOF'" in s)
check("3.4 sources для gnome", "('xkb', 'us'), ('xkb', 'ru')" in s)
check("3.5 /etc/environment жив", "XKB_DEFAULT_LAYOUT=us,ru" in s)
check("3.6 брендинг на месте", "PRETTY_NAME=\"Ouvert Linux\"" in s)
check("3.7 чистка репо на месте", "sed -i '/^\\[ouvert\\]$/,+2d'" in s)

print("=== 4. Гейт: раскладка одна -> раскладочных слоёв нет ===")
for kb in ("us", "ru"):
    t = gen(kb)
    check(f"4.{kb} vconsole не пишется", "VCEOF" not in t)
    check(f"4.{kb} 00-keyboard не пишется", "XORGEOF" not in t)
    check(f"4.{kb} kxkbrc не пишется", "KXKBEOF" not in t)
    check(f"4.{kb} брендинг всё равно есть", "PRETTY_NAME" in t)

print("=== 5. bash -n на КАЖДОЙ сгенерированной команде ===")
cmds = config_gen.build_custom_commands({"kb": "us_ru"})
for i, c in enumerate(cmds, 1):
    p = subprocess.run(["bash", "-n"], input=c, text=True,
                       capture_output=True)
    check(f"5.{i} команда {i} синтаксически валидна",
          p.returncode == 0, p.stderr.strip())

print("=== 6. Боевой прогон vconsole-команды на фейковом /etc ===")
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "etc" / "X11" / "xorg.conf.d").mkdir(parents=True)
    # то, что оставляет archinstall: KEYMAP + FONT, без XKB*
    (root / "etc" / "vconsole.conf").write_text(
        "# Written by systemd-firstboot(1)\nKEYMAP=ru\nFONT=cyr-sun16\n")
    # берём ТУ САМУЮ команду из вывода, а не переписываем её руками
    found = [c for c in cmds if "VCEOF" in c]
    check("6.0 команда записи vconsole вообще есть", bool(found))
    vc = found[0] if found else ":\n"
    vc_local = vc.replace("/etc/", f"{root}/etc/")
    p = subprocess.run(["bash", "-e"], input=vc_local, text=True,
                       capture_output=True)
    check("6.1 команда отработала", p.returncode == 0, p.stderr.strip())
    got = (root / "etc" / "vconsole.conf").read_text()
    check("6.2 FONT сохранён (его пишет archinstall)", "FONT=cyr-sun16" in got)
    check("6.3 KEYMAP=ru затёрт на us",
          "KEYMAP=us" in got and "KEYMAP=ru" not in got)
    check("6.4 XKBLAYOUT доехал", "XKBLAYOUT=us,ru" in got)
    check("6.5 XKBOPTIONS доехал", "XKBOPTIONS=grp:alt_shift_toggle" in got)
    # повторный прогон = идемпотентность (установка может гоняться дважды)
    subprocess.run(["bash", "-e"], input=vc_local, text=True,
                   capture_output=True)
    got2 = (root / "etc" / "vconsole.conf").read_text()
    check("6.6 повтор не задваивает XKBLAYOUT",
          got2.count("XKBLAYOUT=") == 1,
          f"count={got2.count('XKBLAYOUT=')}")
    check("6.7 повтор не задваивает KEYMAP",
          got2.count("KEYMAP=") == 1, f"count={got2.count('KEYMAP=')}")

print("=== 7. Боевой прогон 00-keyboard.conf ===")
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "etc").mkdir(parents=True)
    found = [c for c in cmds if "XORGEOF" in c]
    check("7.0 команда записи 00-keyboard вообще есть", bool(found))
    xk = found[0] if found else ":\n"
    xk_local = xk.replace("/etc/", f"{root}/etc/")
    p = subprocess.run(["bash", "-e"], input=xk_local, text=True,
                       capture_output=True)
    check("7.1 команда отработала", p.returncode == 0, p.stderr.strip())
    f = root / "etc" / "X11" / "xorg.conf.d" / "00-keyboard.conf"
    check("7.2 файл создан", f.exists())
    if f.exists():
        got = f.read_text()
        check("7.3 секция InputClass", 'Section "InputClass"' in got)
        check("7.4 layout наш", '"XkbLayout" "us,ru"' in got)

print()
print(f"ИТОГО: {ok} ok, {fail} FAIL")
sys.exit(1 if fail else 0)
