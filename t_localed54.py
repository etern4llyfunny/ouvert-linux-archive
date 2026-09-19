#!/usr/bin/env python3
"""КОНТРОЛЬНЫЙ ПРОГОН патча 54 — localed как единый нижний слой.
ОБЯЗАН УПАСТЬ на коде с патчем 51 (до 54).
Запуск: python3 t_localed54.py
"""
import sys
import config_gen

ok, bad = [], []


def check(name, cond):
    (ok if cond else bad).append(name)


def cmds_for(kb):
    return "\n".join(config_gen.build_custom_commands({"kb": kb}))


s = cmds_for("us_ru")

# --- 1. localed стал нижним слоем ---
check("1.1 localectl вызывается", "localectl set-x11-keymap" in s)
check("1.2 layout из таблицы", '"us,ru"' in s)
check("1.3 variant две пустых", 'set-x11-keymap "us,ru" "pc105+inet" ","' in s)
check("1.4 opts из таблицы", '"grp:alt_shift_toggle"' in s)
check("1.5 не валит установку", "|| true" in s)

# --- 2. чужие файлы больше не пишем ---
check("2.1 00-keyboard.conf НЕ пишем", "00-keyboard.conf" not in s)
check("2.2 xorg.conf.d НЕ трогаем", "xorg.conf.d" not in s)
check("2.3 COSMIC-файл НЕ пишем", "CosmicComp" not in s)
check("2.4 heredoc CXKBEOF убран", "CXKBEOF" not in s)

# --- 3. остальные слои ЖИВЫ ---
check("3.1 kxkbrc жив (KDE)", "/etc/skel/.config/kxkbrc" in s)
check("3.2 dconf жив (GNOME)", "02-pzhavos-keyboard" in s)
check("3.3 cinnamon жив", "org/cinnamon/desktop/input-sources" in s)
check("3.4 environment жив", "XKB_DEFAULT_LAYOUT=us,ru" in s)
check("3.5 обои COSMIC живы", "CosmicBackground" in s)
check("3.6 flathub жив", "flathub" in s)

# --- 4. us / ru: localectl НЕ зовём ---
for kb in ("us", "ru"):
    check(f"4.{kb} без localectl", "localectl" not in cmds_for(kb))

for n in ok:
    print(f"  \u2714 {n}")
for n in bad:
    print(f"  \u2718 {n}")
print(f"\nПРОЙДЕНО {len(ok)} / {len(ok) + len(bad)}")
sys.exit(1 if bad else 0)
