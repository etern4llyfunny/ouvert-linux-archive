#!/usr/bin/env python3
"""КОНТРОЛЬНЫЙ ПРОГОН патча 51 — Alt+Shift в COSMIC.

ОБЯЗАН УПАСТЬ на непропатченном config_gen.py (правило 13.5).
Запуск:  python3 t_cosmic51.py
"""
import sys
import importlib

import config_gen
importlib.reload(config_gen)

PATH = "/.config/cosmic/com.system76.CosmicComp/v1"
ok, bad = [], []


def check(name, cond):
    (ok if cond else bad).append(name)


def cmds_for(kb):
    return "\n".join(config_gen.build_custom_commands({"kb": kb}))


# ---------- 1. kb = us_ru: файл ДОЛЖЕН генерироваться ----------
s = cmds_for("us_ru")
check("1.1 путь xkb_config присутствует", PATH in s and "xkb_config" in s)
check("1.2 heredoc CXKBEOF открыт", "<<'CXKBEOF'" in s)
check("1.3 heredoc CXKBEOF закрыт", s.count("CXKBEOF") == 2)
check("1.4 layout из таблицы KB_LAYOUTS", 'layout: "us,ru"' in s)
check("1.5 variant две пустых", 'variant: ","' in s)
check("1.6 options из таблицы", 'options: Some("grp:alt_shift_toggle")' in s)
check("1.7 НЕ затираем чужой файл", '[ ! -e "$d/xkb_config" ]' in s)
check("1.8 chown на месте (было 3, стало 4)", s.count('chown -R "$u:$u"') >= 4)
check("1.9 model НЕ навязан", "pc105" not in s)
check("1.10 repeat_* НЕ навязан", "repeat_delay" not in s and "repeat_rate" not in s)

# ---------- 2. kb = us / ru: файла быть НЕ ДОЛЖНО ----------
for kb in ("us", "ru"):
    check(f"2.{kb} без COSMIC-файла", "CosmicComp" not in cmds_for(kb))

# ---------- 3. старые слои не сломаны ----------
check("3.1 kxkbrc жив", "/etc/skel/.config/kxkbrc" in s)
check("3.2 dconf жив", "02-pzhavos-keyboard" in s)
check("3.3 environment жив", "XKB_DEFAULT_LAYOUT=us,ru" in s)
check("3.4 xorg.conf.d жив", "00-keyboard.conf" in s)

# ---------- итог ----------
for n in ok:
    print(f"  ✔ {n}")
for n in bad:
    print(f"  ✘ {n}")
print(f"\nПРОЙДЕНО {len(ok)} / {len(ok) + len(bad)}")
sys.exit(1 if bad else 0)
