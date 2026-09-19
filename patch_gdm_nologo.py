#!/usr/bin/env python3
"""
patch_gdm_nologo.py — гасит arch-лого на экране логина GDM (навсегда).

Проблема: если в системе включён GDM, на экране логина снизу рисуется лого
дистрибутива (arch-лого из /usr/share/pixmaps). Это протечка бренда: юзер
поставил PzhavOS, а видит Arch. На дефолте у нас XFCE+LightDM (там лого нет),
НО юзер может доставить GNOME+GDM руками (по совету бота) — и лого всплывёт.

Решение: dconf-ключ org.gnome.login-screen logo='' (проверено на живой ВМ —
лого исчезает в ноль). Кладём БЕЗУСЛОВНО (а не под 'if pacman -Q gdm'), чтобы
заглушка уже лежала к моменту, когда юзер доставит gdm потом.

Подвох, который решаем заодно: чтобы logo='' применился, dconf-база gdm должна
быть СКОМПИЛИРОВАНА (dconf update), а для этого нужен бинарь dconf на момент
установки. На XFCE его может не быть → добавляем 'dconf' в PACKAGES, тогда
'dconf update' (он уже вызывается ниже в косметическом блоке) точно отработает
и скомпилит заглушку. Без этого «никогда» ломается.

Что делает скрипт (обе копии config_gen.py):
  1. Заменяет GDM-блок этапа 3: убирает 'if pacman -Q gdm', убирает подстановку
     нашего лого (06-pzhavos-logo), кладёт БЕЗУСЛОВНО профиль gdm +
     07-pzhavos-nologo с logo=''.
  2. Добавляет "dconf" в PACKAGES (официальные репозитории).

Свойства: идемпотентный (маркер 07-pzhavos-nologo), assert по якорям,
обе копии, py_compile в конце.

Запуск (ХОСТ):
  python3 patch_gdm_nologo.py
"""
import subprocess
import sys

DEFAULT_PATHS = [
    "/home/admin/pzhavos/installer/config_gen.py",
    "/home/admin/pzhavos/iso/profile/airootfs/opt/pzhavos-installer/config_gen.py",
]

MARKER = "07-pzhavos-nologo"

# --- Замена 1: GDM-блок ---
OLD_GDM = r'''        # GDM: лого на экране логина. Механизм ArchWiki: dconf-профиль gdm
        # + база /etc/dconf/db/gdm.d + dconf update (работает в чруте,
        # демон не нужен — это компиляция текстовых баз в бинарные).
        "if pacman -Q gdm >/dev/null 2>&1; then\n"
        "  mkdir -p /etc/dconf/profile /etc/dconf/db/gdm.d\n"
        "  [ -f /etc/dconf/profile/gdm ] || cat > /etc/dconf/profile/gdm <<'GDMPEOF'\n"
        "user-db:user\n"
        "system-db:gdm\n"
        "file-db:/usr/share/gdm/greeter-dconf-defaults\n"
        "GDMPEOF\n"
        "  cat > /etc/dconf/db/gdm.d/06-pzhavos-logo <<'GDMLEOF'\n"
        "[org/gnome/login-screen]\n"
        "logo='/usr/share/pixmaps/pzhavos.png'\n"
        "GDMLEOF\n"
        "fi\n"
'''

NEW_GDM = r'''        # GDM: гасим лого дистрибутива на экране логина. Без явного logo GDM
        # рисует фолбэк — arch-лого из /usr/share/pixmaps. Ставим logo='' и
        # делаем это БЕЗУСЛОВНО (не под 'if pacman -Q gdm'): на дефолте у нас
        # XFCE+LightDM и gdm нет, но если юзер доставит gdm потом — заглушка
        # уже на месте, arch-лого не мелькнёт. dconf-база компилится ниже
        # ('dconf update'); dconf добавлен в PACKAGES -> command -v dconf истина.
        "mkdir -p /etc/dconf/profile /etc/dconf/db/gdm.d\n"
        "[ -f /etc/dconf/profile/gdm ] || cat > /etc/dconf/profile/gdm <<'GDMPEOF'\n"
        "user-db:user\n"
        "system-db:gdm\n"
        "file-db:/usr/share/gdm/greeter-dconf-defaults\n"
        "GDMPEOF\n"
        "cat > /etc/dconf/db/gdm.d/07-pzhavos-nologo <<'GDMLEOF'\n"
        "[org/gnome/login-screen]\n"
        "logo=''\n"
        "GDMLEOF\n"
'''

# --- Замена 2: dconf в PACKAGES ---
OLD_PKG = r'''    "ipset",  # optdepends zapret2: нужен для режима iptables
'''
NEW_PKG = r'''    "dconf",  # чтобы dconf update скомпилил заглушку gdm-лого даже без gdm
    "ipset",  # optdepends zapret2: нужен для режима iptables
'''


def patch_one(path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    if MARKER in text:
        print(f"SKIP  (уже пропатчен): {path}")
        return

    assert text.count(OLD_GDM) == 1, f"GDM-якорь встретился {text.count(OLD_GDM)} раз (ждали 1): {path}"
    assert text.count(OLD_PKG) == 1, f"PKG-якорь встретился {text.count(OLD_PKG)} раз (ждали 1): {path}"

    text = text.replace(OLD_GDM, NEW_GDM)
    text = text.replace(OLD_PKG, NEW_PKG)

    # Пост-проверки в памяти до записи.
    assert MARKER in text, f"пост: маркер не появился: {path}"
    assert "06-pzhavos-logo" not in text, f"пост: старый 06-pzhavos-logo остался: {path}"
    assert "if pacman -Q gdm >/dev/null" not in text, f"пост: условие gdm не убрано: {path}"

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
