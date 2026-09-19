#!/usr/bin/env python3
"""
patch_config_kde.py — добавляет в config_gen ветку KDE-обоев (этап 3).

KDE Plasma держит дефолтные обои в наборе Next (пакет plasma-workspace-wallpapers).
Задать дефолт в Plasma без правки конфига под конкретный монитор нельзя, поэтому
подменяем СОДЕРЖИМОЕ набора Next нашим pzhav-kde.png — новый юзер получает Next
и видит наш фон. Тот же приём, что уже работает для XFCE (проверено на t14).

Что делает (обе копии config_gen.py): в косметический блок этапа 3, сразу ПОСЛЕ
XFCE-ветки, вставляет guard 'if [ -d /usr/share/wallpapers/Next/contents ]' и цикл
подмены всех файлов Next (images + images_dark) на pzhav-kde.png. Ветка срабатывает
только если KDE установлен (иначе каталога Next нет).

Свойства: идемпотентный (маркер pzhav-kde.png), assert по якорю, обе копии, py_compile.

Запуск (ХОСТ):
  python3 patch_config_kde.py
"""
import subprocess
import sys

DEFAULT_PATHS = [
    "/home/admin/pzhavos/installer/config_gen.py",
    "/home/admin/pzhavos/iso/profile/airootfs/opt/pzhavos-installer/config_gen.py",
]

MARKER = "pzhav-kde.png"

# Якорь — вся XFCE-ветка обоев (уникальна). KDE-ветку вставляем сразу после неё.
OLD = r'''        "if [ -d /usr/share/backgrounds/xfce ]; then\n"
        "  for f in /usr/share/backgrounds/xfce/*; do\n"
        "    cp -f /usr/share/wallpapers/PzhavOS/pzhav.png \"$f\" || true\n"
        "  done\n"
        "fi\n"
'''

NEW = r'''        "if [ -d /usr/share/backgrounds/xfce ]; then\n"
        "  for f in /usr/share/backgrounds/xfce/*; do\n"
        "    cp -f /usr/share/wallpapers/PzhavOS/pzhav.png \"$f\" || true\n"
        "  done\n"
        "fi\n"
        # KDE Plasma: свои обои pzhav-kde.png. Дефолт в Plasma без правки
        # конфига под монитор не задать, поэтому подменяем содержимое
        # ДЕФОЛТНОГО набора Next (пакет plasma-workspace-wallpapers): новый
        # юзер получает Next -> видит наш фон. Есть только если KDE стоит.
        # Все разрешения + images_dark, чтобы фон был на любой теме. Проверено t14.
        "if [ -d /usr/share/wallpapers/Next/contents ]; then\n"
        "  for f in /usr/share/wallpapers/Next/contents/images/*.png /usr/share/wallpapers/Next/contents/images_dark/*.png; do\n"
        "    cp -f /usr/share/wallpapers/PzhavOS/pzhav-kde.png \"$f\" || true\n"
        "  done\n"
        "fi\n"
'''


def patch_one(path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    if MARKER in text:
        print(f"SKIP  (уже пропатчен): {path}")
        return

    assert text.count(OLD) == 1, f"XFCE-якорь встретился {text.count(OLD)} раз (ждали 1): {path}"

    text = text.replace(OLD, NEW)

    assert MARKER in text, f"пост: маркер не появился: {path}"
    assert text.count("/usr/share/wallpapers/Next/contents ]; then") == 1, f"пост: guard Next не один: {path}"

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"OK    пропатчен: {path}")


def main(paths):
    for p in paths:
        patch_one(p)
    for p in paths:
        subprocess.run([sys.executable, "-m", "py_compile", p], check=True)
    print("py_compile OK для всех файлов.")


if __name__ == "__main__":
    main(DEFAULT_PATHS)
