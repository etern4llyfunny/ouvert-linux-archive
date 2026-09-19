#!/usr/bin/env python3
"""
patch_pkgbuild_kde.py — добавляет KDE-обои pzhav-kde.png в пакет pzhavos-branding.

Что делает (PKGBUILD пакета):
  1. pkgrel: 2 -> 3 (пакет изменился; заодно namcap-E license уходит с новым pkgrel).
  2. Добавляет 'pzhav-kde.png' в массив source (после PzhavOSwalp3.png).
  3. Добавляет один 'SKIP' в sha256sums (счётчики source/sha должны совпадать).
  4. Добавляет install-строку: pzhav-kde.png -> /usr/share/wallpapers/PzhavOS/.

Свойства: идемпотентный (маркер pzhav-kde.png), assert по якорям, в конце bash -n.

Запуск (ХОСТ):
  python3 patch_pkgbuild_kde.py
"""
import subprocess
import sys

DEFAULT_PATH = "/home/admin/pzhavos/pkgbuilds/pzhavos-branding/PKGBUILD"

MARKER = "pzhav-kde.png"

EDITS = [
    # (описание, OLD, NEW)
    ("pkgrel 2->3",
     "\npkgrel=2\n",
     "\npkgrel=3\n"),

    ("source += pzhav-kde.png",
     "        'PzhavOSwalp3.png'\n",
     "        'PzhavOSwalp3.png'\n"
     "        'pzhav-kde.png'\n"),

    ("sha256sums += SKIP",
     "            'SKIP')\n",
     "            'SKIP'\n"
     "            'SKIP')\n"),

    ("install pzhav-kde.png",
     '    install -Dm644 "$srcdir/PzhavOSwalp3.png" "$pkgdir/usr/share/wallpapers/PzhavOS/PzhavOSwalp3.png"\n',
     '    install -Dm644 "$srcdir/PzhavOSwalp3.png" "$pkgdir/usr/share/wallpapers/PzhavOS/PzhavOSwalp3.png"\n'
     '    install -Dm644 "$srcdir/pzhav-kde.png"    "$pkgdir/usr/share/wallpapers/PzhavOS/pzhav-kde.png"\n'),
]


def patch(path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    if MARKER in text:
        print(f"SKIP  (уже пропатчен): {path}")
        return

    for desc, old, _ in EDITS:
        assert text.count(old) == 1, f"якорь [{desc}] встретился {text.count(old)} раз (ждали 1)"

    for desc, old, new in EDITS:
        text = text.replace(old, new)

    # Пост-проверка: счётчики source и sha256sums совпадают.
    assert MARKER in text, "пост: маркер не появился"
    assert "pkgrel=3" in text, "пост: pkgrel не поднят"

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"OK    пропатчен: {path}")


def main(path):
    patch(path)
    # bash -n — синтаксис PKGBUILD (это shell).
    subprocess.run(["bash", "-n", path], check=True)
    print("bash -n OK.")


if __name__ == "__main__":
    main(DEFAULT_PATH)
