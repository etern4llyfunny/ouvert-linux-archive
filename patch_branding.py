#!/usr/bin/env python3
"""Патч этапа 3 (брендинг) для config_gen.py. Правит ОБЕ копии:
   installer/config_gen.py и iso/profile/.../config_gen.py.

   Что добавляет:
   1. PACKAGES += pzhavos-branding (обои, лого, конфиг fastfetch).
   2. build_custom_commands():
      - /etc/os-release -> PzhavOS (NAME/PRETTY_NAME/ID/LOGO);
      - GRUB: DISTRIBUTOR=PzhavOS + фон grub-bg.png + grub-mkconfig;
      - GDM: лого PzhavOS через dconf-профиль gdm (ArchWiki-механизм);
      - обои по умолчанию: GNOME+Cinnamon (dconf local.d),
        XFCE (подмена дефолтных фонов xfdesktop);
      - fastfetch при открытии терминала (skel + существующие /home/*).

   Запуск (ХОСТ): python patch_branding.py
   Идемпотентен: повторный запуск ничего не ломает.
"""
from pathlib import Path
import sys

FILES = [
    Path("/home/admin/pzhavos/installer/config_gen.py"),
    Path("/home/admin/pzhavos/iso/profile/airootfs/opt/pzhavos-installer/config_gen.py"),
]

ANCHOR_PKG = '    "pzhavmem",\n'
PKG_ADD = '    "pzhavos-branding",  # этап 3: обои, лого, конфиг fastfetch\n'

ANCHOR_RET = "    return cmds\n"

BRANDING_BLOCK = '''\
    # ===================== ЭТАП 3: БРЕНДИНГ =====================
    # Критичная часть: os-release + GRUB. set -e — если сломалось,
    # пусть падает громко, а не тихо оставляет Arch-морду.
    cmds.append(
        "set -e\\n"
        # /etc/os-release на Arch — симлинк на /usr/lib/os-release
        # (пакет filesystem). Файл в /etc перекрывает /usr/lib.
        "rm -f /etc/os-release\\n"
        "cat > /etc/os-release <<'OSREOF'\\n"
        'NAME="PzhavOS"\\n'
        'PRETTY_NAME="PzhavOS"\\n'
        "ID=pzhavos\\n"
        "ID_LIKE=arch\\n"
        "BUILD_ID=rolling\\n"
        'ANSI_COLOR="38;2;69;136;131"\\n'
        # LOGO — имя иконки; pzhavos.png лежит в /usr/share/pixmaps
        # (пакет pzhavos-branding), pixmaps — штатный fallback поиска иконок.
        "LOGO=pzhavos\\n"
        "OSREOF\\n"
        # GRUB: имя в пунктах меню + фоновая картинка.
        "sed -i 's|^#\\\\?GRUB_DISTRIBUTOR=.*|GRUB_DISTRIBUTOR=\\"PzhavOS\\"|' /etc/default/grub\\n"
        "grep -q '^GRUB_BACKGROUND=' /etc/default/grub"
        " && sed -i 's|^GRUB_BACKGROUND=.*|GRUB_BACKGROUND=\\"/usr/share/pzhavos/grub-bg.png\\"|' /etc/default/grub"
        " || echo 'GRUB_BACKGROUND=\\"/usr/share/pzhavos/grub-bg.png\\"' >> /etc/default/grub\\n"
        "grub-mkconfig -o /boot/grub/grub.cfg\\n"
    )

    # Косметика DE. БЕЗ set -e: обои не должны валить установку.
    # Каждый кусок за guard'ом — выполняется только если DE/механизм есть.
    cmds.append(
        # GDM: лого на экране логина. Механизм ArchWiki: dconf-профиль gdm
        # + база /etc/dconf/db/gdm.d + dconf update (работает в чруте,
        # демон не нужен — это компиляция текстовых баз в бинарные).
        "if pacman -Q gdm >/dev/null 2>&1; then\\n"
        "  mkdir -p /etc/dconf/profile /etc/dconf/db/gdm.d\\n"
        "  [ -f /etc/dconf/profile/gdm ] || cat > /etc/dconf/profile/gdm <<'GDMPEOF'\\n"
        "user-db:user\\n"
        "system-db:gdm\\n"
        "file-db:/usr/share/gdm/greeter-dconf-defaults\\n"
        "GDMPEOF\\n"
        "  cat > /etc/dconf/db/gdm.d/06-pzhavos-logo <<'GDMLEOF'\\n"
        "[org/gnome/login-screen]\\n"
        "logo='/usr/share/pixmaps/pzhavos.png'\\n"
        "GDMLEOF\\n"
        "fi\\n"
        # Обои по умолчанию GNOME + Cinnamon: системная dconf-база local.
        # /etc/dconf/profile/user по умолчанию НЕ существует — создаём,
        # иначе system-db:local никто не прочитает.
        "if command -v dconf >/dev/null 2>&1; then\\n"
        "  mkdir -p /etc/dconf/profile /etc/dconf/db/local.d\\n"
        "  [ -f /etc/dconf/profile/user ] || cat > /etc/dconf/profile/user <<'USRPEOF'\\n"
        "user-db:user\\n"
        "system-db:local\\n"
        "USRPEOF\\n"
        "  cat > /etc/dconf/db/local.d/01-pzhavos-background <<'BGEOF'\\n"
        "[org/gnome/desktop/background]\\n"
        "picture-uri='file:///usr/share/wallpapers/PzhavOS/pzhav.png'\\n"
        "picture-uri-dark='file:///usr/share/wallpapers/PzhavOS/pzhav.png'\\n"
        "picture-options='zoom'\\n"
        "\\n"
        "[org/cinnamon/desktop/background]\\n"
        "picture-uri='file:///usr/share/wallpapers/PzhavOS/pzhav.png'\\n"
        "BGEOF\\n"
        "  dconf update || true\\n"
        "fi\\n"
        # XFCE: имена мониторов в xfconf заранее неизвестны (Virtual-1 в ВМ,
        # eDP-1/HDMI-1 на железе) — надёжнее подменить ДЕФОЛТНЫЕ фоны
        # xfdesktop. GdkPixbuf определяет формат по содержимому, не по
        # расширению, так что PNG под именем *.svg рендерится нормально.
        # Минус: обновление пакета xfdesktop вернёт свои файлы (известно,
        # чинится позже pacman-хуком).
        "if [ -d /usr/share/backgrounds/xfce ]; then\\n"
        "  for f in /usr/share/backgrounds/xfce/*; do\\n"
        "    cp -f /usr/share/wallpapers/PzhavOS/pzhav.png \\"$f\\" || true\\n"
        "  done\\n"
        "fi\\n"
        # fastfetch при открытии терминала. /etc/skel/.bashrc принадлежит
        # пакету bash — класть свой skel-файл в pzhavos-branding нельзя
        # (конфликт), поэтому дописываем здесь. custom_commands выполняются
        # ПОСЛЕ создания юзера -> правим и skel (будущие юзеры), и
        # существующие /home/* (уже созданный admin).
        "printf '\\\\n# PzhavOS\\\\ncommand -v fastfetch >/dev/null 2>&1 && fastfetch\\\\n' >> /etc/skel/.bashrc\\n"
        "for h in /home/*; do\\n"
        "  [ -d \\"$h\\" ] || continue\\n"
        "  printf '\\\\n# PzhavOS\\\\ncommand -v fastfetch >/dev/null 2>&1 && fastfetch\\\\n' >> \\"$h/.bashrc\\"\\n"
        "  chown \\"$(basename \\"$h\\"):$(basename \\"$h\\")\\" \\"$h/.bashrc\\" || true\\n"
        "done\\n"
    )
    # =================== КОНЕЦ ЭТАПА 3 ===================

'''


def patch(path: Path) -> None:
    text = path.read_text()

    if "pzhavos-branding" in text:
        print(f"[SKIP] {path} — уже пропатчен")
        return

    assert text.count(ANCHOR_PKG) == 1, f"{path}: якорь PACKAGES не найден/неуникален"
    assert text.count(ANCHOR_RET) == 1, f"{path}: якорь 'return cmds' не найден/неуникален"

    text = text.replace(ANCHOR_PKG, ANCHOR_PKG + PKG_ADD)
    text = text.replace(ANCHOR_RET, BRANDING_BLOCK + ANCHOR_RET)

    path.write_text(text)
    print(f"[OK]   {path} — пропатчен")


def main() -> None:
    missing = [p for p in FILES if not p.exists()]
    if missing:
        for p in missing:
            print(f"[FAIL] нет файла: {p}")
        sys.exit(1)
    for p in FILES:
        patch(p)
    print("\nПроверка: python -c \"import sys; sys.path.insert(0, '<папка>'); ...\" не нужна,")
    print("достаточно: grep -c 'ЭТАП 3' <оба файла>  (должно быть 1 и 1)")


if __name__ == "__main__":
    main()
