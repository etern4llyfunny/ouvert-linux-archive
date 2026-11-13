#!/usr/bin/env python3
"""Готовит сборочную linux-ouvert из свежего linux-cachyos-bore.

  python ouvert_kernel_prep.py <upstream>/linux-cachyos-bore <новый каталог>

Копирует каталог и вносит 5 правок в PKGBUILD. Каждый якорь обязан
встретиться ровно 1 раз, иначе ничего не пишется (upstream поменял
PKGBUILD - смотреть глазами).
"""
import datetime
import pathlib
import shutil
import sys

EDITS = [  # (старое, новое)
    (': "${_processor_opt:=}"\n', ': "${_processor_opt:=generic_v1}"\n'),
    ('    _pkgsuffix="cachyos-${_cpusched}"\n', '    _pkgsuffix="ouvert"\n'),
    ("pkgdesc='Linux BORE + Cachy Sauce scheduler Kernel by CachyOS with other patches and improvements'\n",
     "pkgdesc='Ouvert Linux (BORE scheduler, based on CachyOS)'\n"),
    ("export KBUILD_BUILD_HOST=cachyos\n", "export KBUILD_BUILD_HOST=ouvert\n"),
]
HEADER = ("# Ouvert Linux, {d}: modified from CachyOS linux-cachyos-bore "
          "(https://github.com/CachyOS/linux-cachyos). Changes: pkgbase linux-ouvert, "
          "_processor_opt generic_v1, KBUILD_BUILD_HOST, pkgdesc.\n")


def patch(text: str) -> str:
    bad = [old.strip() for old, _ in EDITS if text.count(old) != 1]
    if bad:
        sys.exit("СТОП, якорь не ровно 1 раз:\n  " + "\n  ".join(bad))
    for old, new in EDITS:
        text = text.replace(old, new)
    return HEADER.format(d=datetime.date.today().isoformat()) + text


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = map(pathlib.Path, sys.argv[1:])
    if dst.exists():
        sys.exit(f"СТОП, {dst} уже существует")
    new = patch((src / "PKGBUILD").read_text())  # проверка до любой записи
    shutil.copytree(src, dst)
    (dst / "PKGBUILD").write_text(new)
    (dst / ".SRCINFO").unlink(missing_ok=True)  # от upstream, с чужим именем пакета
    print(f"OK: {dst}, правок {len(EDITS)} + шапка, PKGBUILD {len(new.encode())} Б")


if __name__ == "__main__":
    main()
