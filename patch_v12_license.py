#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_v12_license.py — добавляет файл LICENSE в пакет pzhavos-branding.

Что делает:
  1. pkgrel=4  ->  pkgrel=5
  2. 'LICENSE' в конец массива source   (13 -> 14 элементов)
  3. ещё один 'SKIP' в sha256sums       (13 -> 14 элементов)
  4. install-строка LICENSE в /usr/share/licenses/pzhavos-branding/

Свойства:
  - ТРАНЗАКЦИОННЫЙ: все якоря проверяются ДО записи хоть одного байта.
  - ИДЕМПОТЕНТНЫЙ:  повторный запуск -> "ИЗМЕНЕНИЙ НЕТ", файл не тронут.
  - С БЭКАПОМ:      PKGBUILD.v12bak (не перезаписывается, если уже есть).
  - С ПРОВЕРКОЙ:    после патча сверяет длины source и sha256sums.
"""

import os
import re
import sys
import shutil

PKGBUILD = os.path.expanduser("~/pzhavos/pkgbuilds/pzhavos-branding/PKGBUILD")
BACKUP = PKGBUILD + ".v12bak"

# ---------------------------------------------------------------- якоря
A1_OLD = "pkgrel=4\n"
A1_NEW = "pkgrel=5\n"

A2_OLD = "        'pzhavos-restore-wallpapers.sh')\n"
A2_NEW = "        'pzhavos-restore-wallpapers.sh'\n        'LICENSE')\n"

A3_OLD = "            'SKIP')\n"
A3_NEW = "            'SKIP'\n            'SKIP')\n"

A4_OLD = ('    install -Dm755 "$srcdir/pzhavos-restore-wallpapers.sh" '
          '"$pkgdir/usr/share/pzhavos/restore-wallpapers.sh"\n')
A4_NEW = (A4_OLD +
          '    # Текст лицензии: license=(LicenseRef-*) обязывает положить\n'
          '    # файл в /usr/share/licenses/$pkgname/ — иначе namcap даёт E.\n'
          '    install -Dm644 "$srcdir/LICENSE" '
          '"$pkgdir/usr/share/licenses/$pkgname/LICENSE"\n')

ANCHORS = [
    ("pkgrel=4", A1_OLD, A1_NEW),
    ("конец массива source", A2_OLD, A2_NEW),
    ("конец массива sha256sums", A3_OLD, A3_NEW),
    ("install-строка restore-wallpapers.sh", A4_OLD, A4_NEW),
]


def fail(msg):
    print("ОТКАЗ: " + msg)
    print("Файл НЕ тронут.")
    sys.exit(1)


def count_array(text, name):
    """Считает число элементов в массиве name=(...) по кавычкам."""
    m = re.search(r"^%s=\((.*?)\)\s*$" % re.escape(name), text,
                  re.S | re.M)
    if not m:
        return -1
    return len(re.findall(r"'[^']*'", m.group(1)))


def main():
    if not os.path.isfile(PKGBUILD):
        fail("не найден %s" % PKGBUILD)

    with open(PKGBUILD, "r", encoding="utf-8") as f:
        text = f.read()

    # ------------------------------------------------ проверка идемпотентности
    already = []
    if "'LICENSE')" in text:
        already.append("LICENSE в source")
    if "usr/share/licenses/$pkgname/LICENSE" in text:
        already.append("install-строка LICENSE")
    if "pkgrel=5\n" in text:
        already.append("pkgrel=5")

    if len(already) == 3:
        print("ИЗМЕНЕНИЙ НЕТ — патч уже применён (%s)." % ", ".join(already))
        sys.exit(0)
    if already:
        fail("частично применён (%s). Разбирайся руками или откатись "
             "на %s." % (", ".join(already), BACKUP))

    # ------------------------------------------------ проверка ВСЕХ якорей
    print("Проверка якорей:")
    problems = []
    for label, old, _new in ANCHORS:
        n = text.count(old)
        print("  [%s] %-38s вхождений: %d" %
              ("OK" if n == 1 else "!!", label, n))
        if n != 1:
            problems.append("%s (найдено %d, ожидалось 1)" % (label, n))
    if problems:
        fail("якоря не сошлись: " + "; ".join(problems))

    # ------------------------------------------------ сверка длин ДО
    n_src = count_array(text, "source")
    n_sha = count_array(text, "sha256sums")
    print("До патча:  source=%d, sha256sums=%d" % (n_src, n_sha))
    if n_src != n_sha:
        fail("массивы уже разъехались (%d vs %d)" % (n_src, n_sha))

    # ------------------------------------------------ применение в памяти
    new_text = text
    for _label, old, new in ANCHORS:
        new_text = new_text.replace(old, new, 1)

    n_src2 = count_array(new_text, "source")
    n_sha2 = count_array(new_text, "sha256sums")
    print("После патча: source=%d, sha256sums=%d" % (n_src2, n_sha2))
    if n_src2 != n_sha2:
        fail("после патча массивы разной длины (%d vs %d)" % (n_src2, n_sha2))
    if n_src2 != n_src + 1:
        fail("source вырос не на 1 (%d -> %d)" % (n_src, n_src2))

    if new_text == text:
        fail("текст не изменился — этого быть не должно")

    # ------------------------------------------------ бэкап и запись
    if not os.path.exists(BACKUP):
        shutil.copy2(PKGBUILD, BACKUP)
        print("Бэкап: %s" % BACKUP)
    else:
        print("Бэкап уже существует, не перезаписываю: %s" % BACKUP)

    with open(PKGBUILD, "w", encoding="utf-8") as f:
        f.write(new_text)

    print("ГОТОВО. Изменений: 4 (pkgrel, source, sha256sums, package()).")
    print("Проверь синтаксис:  bash -n %s" % PKGBUILD)


if __name__ == "__main__":
    main()
