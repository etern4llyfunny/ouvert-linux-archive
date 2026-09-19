#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PzhavOS — патч «Bug 47 cosmic»: обои COSMIC.

ЧТО ДЕЛАЕТ
  1. pkgbuilds/pzhavos-branding/PKGBUILD
       pkgrel 5 -> 6
       source:      + pzhav-cosmic.png, cosmic-bg-all, cosmic-bg-backgrounds
       sha256sums:  + три 'SKIP'
       package():   + PNG в /usr/share/wallpapers/PzhavOS/
                    + два RON-ключа в /etc/skel/.config/cosmic/...
  2. installer/config_gen.py
       новый блок в build_custom_commands: разнос RON по существующим /home/*
       (юзер создаётся ДО установки пакетов — доказано логом t11)
  3. создаёт рядом с PKGBUILD два файла-ключа: cosmic-bg-all, cosmic-bg-backgrounds

СВОЙСТВА
  - ТРАНЗАКЦИОННЫЙ: все якоря во всех файлах проверяются ДО записи первого байта
  - ИДЕМПОТЕНТНЫЙ:  маркер «Bug 47 cosmic» дословно в ОБОИХ файлах, проверяется
                    в каждом отдельно
  - ПРЕДУСЛОВИЯ:    размеры 3541 и 36989, сверяются и называются вслух
  - ОТКАТ:          если второй файл не записался — первый возвращается из бэкапа
  - БЭКАПЫ:         рядом с исходником, с меткой времени

ЗАПУСК: python3 patch_cosmic47.py [корень_проекта]
        по умолчанию корень = ~/pzhavos
"""

import os
import sys
import shutil
from datetime import datetime

MARKER = "Bug 47 cosmic"
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")

EXPECT_PKGBUILD = 3541
EXPECT_CONFIG_GEN = 36989


def die(msg):
    print("✘ ОСТАНОВ: " + msg)
    sys.exit(1)


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def nbytes(text):
    # 13.18: размер только в байтах, len() на кириллице врёт вдвое
    return len(text.encode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# СОДЕРЖИМОЕ ДВУХ RON-КЛЮЧЕЙ
# Схема снята с живого пакета cosmic-bg 1:1.5.0-1,
# файл /usr/share/cosmic/com.system76.CosmicBackground/v1/all — не выдумана.
# Отличие от дефолта System76: свой source и filter_by_theme false
# (отбор по светлой/тёмной теме осмыслен для каталога, у нас один файл).
# ─────────────────────────────────────────────────────────────────────────────
RON_ALL = '''(
    output: "all",
    source: Path("/usr/share/wallpapers/PzhavOS/pzhav-cosmic.png"),
    filter_by_theme: false,
    rotation_frequency: 3600,
    filter_method: Lanczos,
    scaling_mode: Zoom,
    sampling_method: Alphanumeric,
)
'''

RON_BACKGROUNDS = "[All]\n"


# ─────────────────────────────────────────────────────────────────────────────
# ЯКОРЯ И ЗАМЕНЫ — PKGBUILD
# ─────────────────────────────────────────────────────────────────────────────
PKG_EDITS = [
    (
        "pkgrel=5\n",
        "pkgrel=6\n",
    ),
    (
        "        'pzhavos-restore-wallpapers.sh'\n"
        "        'LICENSE')\n",

        "        'pzhavos-restore-wallpapers.sh'\n"
        "        'pzhav-cosmic.png'\n"
        "        'cosmic-bg-all'\n"
        "        'cosmic-bg-backgrounds'\n"
        "        'LICENSE')\n",
    ),
    (
        "            'SKIP')\n",

        "            'SKIP'\n"
        "            'SKIP'\n"
        "            'SKIP'\n"
        "            'SKIP')\n",
    ),
    (
        '    install -Dm644 "$srcdir/pzhav-kde.png"    '
        '"$pkgdir/usr/share/wallpapers/PzhavOS/pzhav-kde.png"\n',

        '    install -Dm644 "$srcdir/pzhav-kde.png"    '
        '"$pkgdir/usr/share/wallpapers/PzhavOS/pzhav-kde.png"\n'
        "    # " + MARKER + ": обои COSMIC\n"
        '    install -Dm644 "$srcdir/pzhav-cosmic.png" '
        '"$pkgdir/usr/share/wallpapers/PzhavOS/pzhav-cosmic.png"\n',
    ),
    (
        '    install -Dm644 "$srcdir/fastfetch-config.jsonc" '
        '"$pkgdir/etc/skel/.config/fastfetch/config.jsonc"\n',

        '    install -Dm644 "$srcdir/fastfetch-config.jsonc" '
        '"$pkgdir/etc/skel/.config/fastfetch/config.jsonc"\n'
        "\n"
        "    # " + MARKER + ": штатный оверрайд cosmic-config.\n"
        "    # Системный дефолт лежит в /usr/share/cosmic/ и принадлежит пакету\n"
        "    # cosmic-bg — писать туда НЕЛЬЗЯ (конфликт файлов в pacman и\n"
        "    # перезапись при -Syu). Пользовательский слой ~/.config/cosmic/\n"
        "    # ничей, поэтому кладём в /etc/skel. Хук restore-wallpapers.sh\n"
        "    # здесь не нужен: чужих файлов не трогаем, восстанавливать нечего.\n"
        '    install -Dm644 "$srcdir/cosmic-bg-all" '
        '"$pkgdir/etc/skel/.config/cosmic/com.system76.CosmicBackground/v1/all"\n'
        '    install -Dm644 "$srcdir/cosmic-bg-backgrounds" '
        '"$pkgdir/etc/skel/.config/cosmic/com.system76.CosmicBackground/v1/backgrounds"\n',
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# ЯКОРЬ И ЗАМЕНА — config_gen.py
# Якорь трёхстрочный: одиночное "for h in /home/*; do" встречается ТРИЖДЫ
# (строки 181, 365, 376) и якорем быть не может. Строка с pzhav-kde.png —
# уникальна.
# ─────────────────────────────────────────────────────────────────────────────
CG_ANCHOR = (
    '        "    cp -f /usr/share/wallpapers/PzhavOS/pzhav-kde.png \\"$f\\" || true\\n"\n'
    '        "  done\\n"\n'
    '        "fi\\n"\n'
)

CG_INSERT = (
    "        # ★ " + MARKER + ": обои COSMIC.\n"
    "        # Здесь НЕ подмена чужих файлов, как в XFCE/KDE выше, а штатный\n"
    "        # оверрайд cosmic-config. Системный дефолт /usr/share/cosmic/\n"
    "        # принадлежит пакету cosmic-bg — туда писать нельзя. Свои ключи\n"
    "        # кладёт pzhavos-branding в /etc/skel, здесь разносим их по уже\n"
    "        # созданным /home/* (юзер создаётся ДО пакетов — лог t11).\n"
    "        # Условие по каталогу, а не по выбору DE в GUI: юзер мог доставить\n"
    "        # COSMIC вторым столом. Та же логика, что у блока Next выше.\n"
    "        # Схема RON снята с живого cosmic-bg 1:1.5.0-1, не выдумана.\n"
    '        "if [ -d /usr/share/cosmic ] &&'
    ' [ -f /etc/skel/.config/cosmic/com.system76.CosmicBackground/v1/all ]; then\\n"\n'
    '        "  for h in /home/*; do\\n"\n'
    '        "    [ -d \\"$h\\" ] || continue\\n"\n'
    '        "    u=$(basename \\"$h\\")\\n"\n'
    '        "    d=\\"$h/.config/cosmic/com.system76.CosmicBackground/v1\\"\\n"\n'
    '        "    if [ ! -e \\"$d/all\\" ]; then\\n"\n'
    '        "      mkdir -p \\"$d\\"\\n"\n'
    '        "      cp /etc/skel/.config/cosmic/com.system76.CosmicBackground/v1/all'
    ' \\"$d/\\" || true\\n"\n'
    '        "      cp /etc/skel/.config/cosmic/com.system76.CosmicBackground/v1/backgrounds'
    ' \\"$d/\\" || true\\n"\n'
    '        "      chown -R \\"$u:$u\\" \\"$h/.config\\" 2>/dev/null || true\\n"\n'
    '        "    fi\\n"\n'
    '        "  done\\n"\n'
    '        "fi\\n"\n'
)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/pzhavos")
    root = os.path.abspath(root)

    pkg_dir = os.path.join(root, "pkgbuilds", "pzhavos-branding")
    pkg_path = os.path.join(pkg_dir, "PKGBUILD")
    cg_path = os.path.join(root, "installer", "config_gen.py")

    print("=" * 72)
    print("  ПАТЧ «" + MARKER + "» — обои COSMIC")
    print("  корень: " + root)
    print("=" * 72)

    # ── ФАЗА 1: ПРЕДУСЛОВИЯ ──────────────────────────────────────────────
    print("\n[1/5] ПРЕДУСЛОВИЯ")

    for p in (pkg_path, cg_path):
        if not os.path.isfile(p):
            die("нет файла: " + p)
    print("  ✔ оба файла на месте")

    png = os.path.join(pkg_dir, "pzhav-cosmic.png")
    if not os.path.isfile(png):
        die("нет " + png + "\n"
            "    Сначала: cp ~/Загрузки/pzhavcosmic.png " + png)
    print("  ✔ pzhav-cosmic.png на месте (%d Б)" % os.path.getsize(png))

    pkg_txt = read(pkg_path)
    cg_txt = read(cg_path)

    pkg_n = nbytes(pkg_txt)
    cg_n = nbytes(cg_txt)
    print("  PKGBUILD      %d Б (ждали %d)" % (pkg_n, EXPECT_PKGBUILD))
    print("  config_gen.py %d Б (ждали %d)" % (cg_n, EXPECT_CONFIG_GEN))

    # ── ФАЗА 2: ИДЕМПОТЕНТНОСТЬ ──────────────────────────────────────────
    # 13.29: маркер проверяется в КАЖДОМ файле отдельно; «применена половина»
    # обязана быть видна, а не замазана.
    print("\n[2/5] ИДЕМПОТЕНТНОСТЬ (маркер «%s»)" % MARKER)
    in_pkg = MARKER in pkg_txt
    in_cg = MARKER in cg_txt
    print("  PKGBUILD      маркер: %s" % ("ЕСТЬ" if in_pkg else "нет"))
    print("  config_gen.py маркер: %s" % ("ЕСТЬ" if in_cg else "нет"))

    if in_pkg and in_cg:
        print("\n✔ Патч УЖЕ ПРИМЕНЁН к обоим файлам. Ничего не делаю.")
        return 0
    if in_pkg != in_cg:
        die("ПРИМЕНЕНА ПОЛОВИНА ПАТЧА. Руками не чинить — откатить из\n"
            "    бэкапов *.b47bak-* и запустить заново.")

    if pkg_n != EXPECT_PKGBUILD or cg_n != EXPECT_CONFIG_GEN:
        die("размеры не сошлись, а маркера нет — дерево НЕ то, что ожидалось.\n"
            "    Правило 13.26: работа не начинается.\n"
            "    Первая команда расследования:\n"
            "      ls -l --time-style=full-iso " + pkg_dir + "\n"
            "      ls -l --time-style=full-iso " + os.path.dirname(cg_path))
    print("  ✔ размеры сошлись")

    # ── ФАЗА 3: ВСЕ ЯКОРЯ, ДО ЕДИНОЙ ЗАПИСИ ──────────────────────────────
    print("\n[3/5] ЯКОРЯ (проверка на КОЛИЧЕСТВО вхождений)")
    problems = []

    for i, (old, _new) in enumerate(PKG_EDITS, 1):
        c = pkg_txt.count(old)
        head = old.strip().splitlines()[0][:58]
        print("  PKGBUILD  #%d: %d вхожд.  %s" % (i, c, head))
        if c != 1:
            problems.append("PKGBUILD якорь #%d: вхождений %d, нужно 1" % (i, c))

    c = cg_txt.count(CG_ANCHOR)
    print("  config_gen #1: %d вхожд.  (трёхстрочный, по pzhav-kde.png)" % c)
    if c != 1:
        problems.append("config_gen якорь: вхождений %d, нужно 1" % c)

    if problems:
        print()
        for p in problems:
            print("  ✘ " + p)
        die("якоря не сошлись. НИ ОДИН байт не записан.")
    print("  ✔ все якоря уникальны")

    # ── ФАЗА 4: ЗАПИСЬ ───────────────────────────────────────────────────
    print("\n[4/5] ЗАПИСЬ")

    new_pkg = pkg_txt
    for old, new in PKG_EDITS:
        new_pkg = new_pkg.replace(old, new, 1)
    new_cg = cg_txt.replace(CG_ANCHOR, CG_ANCHOR + CG_INSERT, 1)

    # страховка: маркер обязан оказаться в ОБОИХ результатах
    if MARKER not in new_pkg or MARKER not in new_cg:
        die("маркер не попал в результат — замены собраны неверно. Не пишу.")

    pkg_bak = pkg_path + ".b47bak-" + STAMP
    cg_bak = cg_path + ".b47bak-" + STAMP
    shutil.copy2(pkg_path, pkg_bak)
    shutil.copy2(cg_path, cg_bak)
    print("  бэкап: " + os.path.basename(pkg_bak))
    print("  бэкап: " + os.path.basename(cg_bak))

    with open(pkg_path, "w", encoding="utf-8") as f:
        f.write(new_pkg)
    print("  ✔ PKGBUILD записан")

    try:
        with open(cg_path, "w", encoding="utf-8") as f:
            f.write(new_cg)
        print("  ✔ config_gen.py записан")
    except Exception as e:
        shutil.copy2(pkg_bak, pkg_path)
        die("config_gen.py не записался (%s). PKGBUILD ОТКАЧЁН из бэкапа." % e)

    # два ключа рядом с PKGBUILD
    for name, body in (("cosmic-bg-all", RON_ALL),
                       ("cosmic-bg-backgrounds", RON_BACKGROUNDS)):
        p = os.path.join(pkg_dir, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
        print("  ✔ создан %s (%d Б)" % (name, os.path.getsize(p)))

    # ── ФАЗА 5: ПРОВЕРКА ПОСЛЕ (13.16) ───────────────────────────────────
    print("\n[5/5] ПРОВЕРКА ПОСЛЕ ЗАПИСИ")
    a = read(pkg_path)
    b = read(cg_path)
    ok = True

    checks = [
        ("PKGBUILD: маркер", MARKER in a),
        ("PKGBUILD: pkgrel=6", "pkgrel=6\n" in a),
        ("PKGBUILD: pzhav-cosmic.png в source", "'pzhav-cosmic.png'" in a),
        ("PKGBUILD: cosmic-bg-all в source", "'cosmic-bg-all'" in a),
        ("PKGBUILD: cosmic-bg-backgrounds в source", "'cosmic-bg-backgrounds'" in a),
        ("PKGBUILD: 17 строк SKIP", a.count("'SKIP'") == 17),
        ("PKGBUILD: install skel/all", "CosmicBackground/v1/all\"" in a),
        ("PKGBUILD: install skel/backgrounds", "CosmicBackground/v1/backgrounds\"" in a),
        ("config_gen: маркер", MARKER in b),
        ("config_gen: гейт /usr/share/cosmic", "if [ -d /usr/share/cosmic ]" in b),
        ("config_gen: python синтаксис", None),
    ]
    for name, res in checks:
        if res is None:
            continue
        print("  %s %s" % ("✔" if res else "✘", name))
        ok = ok and res

    try:
        compile(b, cg_path, "exec")
        print("  ✔ config_gen: python синтаксис")
    except SyntaxError as e:
        print("  ✘ config_gen: СИНТАКСИС СЛОМАН — %s" % e)
        ok = False

    n_a, n_b = nbytes(a), nbytes(b)
    print("\n  PKGBUILD      %d -> %d Б  (+%d)" % (pkg_n, n_a, n_a - pkg_n))
    print("  config_gen.py %d -> %d Б  (+%d)" % (cg_n, n_b, n_b - cg_n))

    if not ok:
        die("проверки после записи ПРОВАЛЕНЫ. Откатывай из бэкапов *.b47bak-" + STAMP)

    print("\n✔ ПАТЧ ПРИМЕНЁН. Дальше: makepkg -f, repo-add, бамп iso_version.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
