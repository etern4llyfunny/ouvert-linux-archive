"""Генерация конфигов для archinstall 4.4 (--config/--creds --silent).

ВЕРСИЯ: см. строку VERSION ниже (маркер свежести: grep -n "^VERSION" config_gen.py)

Формат сверен ТОЛЬКО по исходникам archinstall тега 4.4:
  lib/models/device.py   DiskLayoutConfiguration.parse_arg, Size/SectorSize,
                         PartitionFlag, ModificationStatus, DiskEncryption.parse_arg
  lib/disk/disk_menu.py  suggest_single_disk_layout, _boot_partition,
                         get_default_btrfs_subvols
  lib/disk/filesystem.py форматируются только create+modify, existing не трогается
  lib/installer.py       _add_grub_bootloader: UEFI -> --target=<arch>-efi,
                         BIOS -> --target=i386-pc на родительский диск
  lib/models/bootloader.py  removable по умолчанию True (баг 7!)
  lib/args.py            --config и --creds мержатся в ОДИН dict,
                         encryption_password берётся оттуда же

Ключевые факты, из-за которых план раздела 9 был поправлен:
  * Флага bios_grub / EF02 в 4.4 НЕТ. Флаги только: boot, esp, bls_boot,
    linux-home, swap.
  * Таблица разделов в JSON не задаётся вообще: PartitionTable.default()
    выбирает GPT при UEFI и MBR (msdos) при BIOS по прошивке ЖИВОЙ системы.
  * Unit парсится как Unit[name] — регистр строгий: "MiB", "GiB", "B".
"""
import json
import os
import subprocess
import uuid
from pathlib import Path

from desktops import CUSTOM_SETTINGS

VERSION = "v9"

OUT_DIR = Path("/tmp/ouvert")
CONFIG_PATH = OUT_DIR / "user_configuration.json"
CREDS_PATH = OUT_DIR / "user_credentials.json"

EFI_MARKER = Path("/sys/firmware/efi")

MIB = 2 ** 20
GIB = 2 ** 30

ESP_MIB = 1024        # archinstall: Size(1, Unit.GiB) под /boot
FIRST_START_MIB = 1   # archinstall: is_valid_start() требует >= 1 MiB
ROOT_START_MIB = FIRST_START_MIB + ESP_MIB

FILESYSTEMS = ["ext4", "btrfs", "xfs", "f2fs"]

# Точная копия get_default_btrfs_subvols() из archinstall 4.4
DEFAULT_SUBVOLS = [
    {"name": "@", "mountpoint": "/"},
    {"name": "@home", "mountpoint": "/home"},
    {"name": "@log", "mountpoint": "/var/log"},
    {"name": "@pkg", "mountpoint": "/var/cache/pacman/pkg"},
]

MOUNTPOINTS = ["/", "/boot", "/efi", "/home", "swap"]

# В ручном режиме комбо ФС шире: для ESP нужен fat32, но предлагать его
# под корень бессмысленно.
MANUAL_FILESYSTEMS = FILESYSTEMS + ["fat32"]

# lsblk называет ФС ПО-СВОЕМУ. Полный список FilesystemType 4.4:
# btrfs ext2 ext3 ext4 f2fs fat12 fat16 fat32 ntfs xfs linux-swap crypto_LUKS.
# 'vfat' там НЕТ -> "'vfat' is not a valid FilesystemType" (баг 15).
VALID_FS = {"btrfs", "ext2", "ext3", "ext4", "f2fs", "fat12", "fat16", "fat32", "ntfs", "xfs"}


def map_lsblk_fs(fstype: str, fsver: str = "") -> str:
    """Имя ФС из lsblk -> имя из FilesystemType. Пустая строка = не пригодно
       для монтирования как есть (UI тогда заставит форматировать)."""
    f = (fstype or "").strip().lower()
    if not f:
        return ""
    if f == "vfat":
        # FAT16 и FAT32 lsblk различает только колонкой FSVER
        v = (fsver or "").upper()
        if "16" in v:
            return "fat16"
        if "12" in v:
            return "fat12"
        return "fat32"
    if f == "swap":
        return "linux-swap"
    if f in VALID_FS:
        return f
    # crypto_LUKS, exfat, zfs и прочее: смонтировать как есть не сможем
    return ""

# Kernel из lib/models/package_types.py 4.4. Других значений нет.
# Патч 65: linux-ouvert нет в enum Kernel, но args.py:328 берёт kernels
# как есть; kernels[0] = ядро по умолчанию в загрузчике (installer.py:1300).
KERNEL_SETS = {
    "ouvert": ["linux-ouvert"],
    "ouvert+lts": ["linux-ouvert", "linux-lts"],
    "linux": ["linux"],
    "linux-lts": ["linux-lts"],
}

# kb_layout проверяется через verify_keyboard_layout() -> localectl list-keymaps.
# Невалидное значение = error в логе, раскладка молча не применится.
# x11: (XkbLayout, XkbOptions) — пишется custom_command'ом, см. build_custom_commands.
# ВАЖНО: при "us_ru" в vconsole.conf уедет KEYMAP=us — это сознательно:
# в TTY всегда можно набрать латиницей логин и пароль.
KB_LAYOUTS = {
    "us": {"kb_layout": "us", "x11": None},
    "us_ru": {"kb_layout": "us", "x11": ("us,ru", "grp:alt_shift_toggle")},
    "ru": {"kb_layout": "ru", "x11": None},
}

# installer.py set_vconsole(): FONT= пишется в /etc/vconsole.conf; если имя
# начинается на "ter-", archinstall сам ставит terminus-font.
# default8x16 НЕ содержит кириллицы -> при sys_lang=ru_RU сообщения в TTY
# превратятся в мусор. Имена НЕ угадываем: берём первый реально существующий
# (kbd есть и на ISO, и в цели, набор одинаковый).
CONSOLE_FONTS_DIR = Path("/usr/share/kbd/consolefonts")
CYRILLIC_FONTS = ["cyr-sun16", "UniCyr_8x16", "LatKaCyrHeb-16", "LatArCyrHeb-16", "Cyr_a8x16"]
DEFAULT_FONT = "default8x16"


def list_console_fonts() -> list[str]:
    """Копия логики list_console_fonts() из archinstall/lib/locale/utils.py."""
    try:
        return sorted({p.name.split(".")[0] for p in CONSOLE_FONTS_DIR.glob("*.gz")})
    except Exception:
        return []


def pick_console_font(lang: str) -> str:
    if lang != "ru":
        return DEFAULT_FONT
    have = set(list_console_fonts())
    for f in CYRILLIC_FONTS:
        if f in have:
            return f
    return DEFAULT_FONT


def build_custom_commands(state: dict) -> list[str]:
    """Шелл-скрипты, выполняемые в чруте ЦЕЛИ после установки
       (installer.py: arch-chroot -S <target> bash script; guided.py:181).
       Это bash, а не fish — heredoc здесь легален.
       archinstall умеет только ОДНУ раскладку (kb_layout), поэтому
       переключатель us,ru делаем файлом сами.
    """
    cmds: list[str] = []
    kb = KB_LAYOUTS.get(state.get("kb") or "us")
    if kb and kb["x11"]:
        layout, opts = kb["x11"]
        # ★ Bug 55 vconsole: НИЖНИЙ СЛОЙ РАСКЛАДКИ — localed, но говорить
        # с ним надо ФАЙЛОМ, а не localectl.
        # Журнал ПЕРВОЙ загрузки beta-4.3 на t27 (снят 13.08.26):
        #   03:24:13 cosmic-greeter-daemon: xkb_config NotFound -> берёт свой
        #            дефолт us + terminate:ctrl_alt_bksp
        #   03:24:22 systemd-localed: X11 layout 'us' converted to VC 'us'
        # То есть COSMIC на старте СПРАШИВАЕТ localed и, если у того
        # X11 пусто, ставит СВОЙ дефолт и пишет его ОБРАТНО.
        # Отсюда «одна раскладка us» на свежей системе.
        # localed хранит X11-раскладку в /etc/vconsole.conf (XKB*), а
        # /etc/X11/xorg.conf.d/00-keyboard.conf только ГЕНЕРИРУЕТ из неё.
        # archinstall пишет в vconsole.conf лишь KEYMAP и FONT -> X11 пусто.
        # Патч 54 (localectl set-x11-keymap) бил в верный этаж, но в чруте
        # не оставил на диске НИ ОДНОГО следа: install.log показывает
        # запуск команды, а файлы не изменились. Класс Bug 46 —
        # инструмент тихо вернул не то. Файл спорить не умеет.
        # ★ ПРОВЕРЕНО КЛИКАМИ на t27 13.08.26: при заполненном localed
        #   COSMIC после ПЕРЕЗАГРУЗКИ даёт Alt+Shift -> «йцукен».
        # KEYMAP пишем принудительно (Bug 53): в аварийной консоли
        # логин и пароль всегда набираются латиницей.
        variant = "," * layout.count(",")
        cmds.append(
            "touch /etc/vconsole.conf\n"
            "sed -i '/^KEYMAP=/d;/^XKBLAYOUT=/d;/^XKBMODEL=/d;"
            "/^XKBVARIANT=/d;/^XKBOPTIONS=/d' /etc/vconsole.conf || true\n"
            "cat >> /etc/vconsole.conf <<'VCEOF'\n"
            f"KEYMAP={kb['kb_layout']}\n"
            f"XKBLAYOUT={layout}\n"
            "XKBMODEL=pc105+inet\n"
            f"XKBVARIANT={variant}\n"
            f"XKBOPTIONS={opts}\n"
            "VCEOF\n"
        )

        # Слой Xorg. COSMIC и KDE-Wayland берут раскладку из localed по
        # D-Bus, а X11-сессии (XFCE+LightDM — наш дефолт) читают
        # именно этот файл. Формально он принадлежит localed (13.40),
        # но гонки нет: localed генерирует его ИЗ vconsole.conf, который
        # мы только что заполнили — перезапись даст тот же текст.
        # Формат снят с живого файла на t27, не выдуман.
        cmds.append(
            "mkdir -p /etc/X11/xorg.conf.d\n"
            "cat > /etc/X11/xorg.conf.d/00-keyboard.conf <<'XORGEOF'\n"
            'Section "InputClass"\n'
            '        Identifier "system-keyboard"\n'
            '        MatchIsKeyboard "on"\n'
            f'        Option "XkbLayout" "{layout}"\n'
            '        Option "XkbModel" "pc105+inet"\n'
            f'        Option "XkbVariant" "{variant}"\n'
            f'        Option "XkbOptions" "{opts}"\n'
            "EndSection\n"
            "XORGEOF\n"
        )

        # --- Ouvert Linux: раскладка для DE, которые X11-файл ИГНОРИРУЮТ ---
        # KDE Plasma на Wayland читает ~/.config/kxkbrc (эталон снят с t18),
        # GNOME/Cinnamon — dconf (org/gnome/desktop/input-sources).
        # Юзер создаётся ДО этих команд -> skel уже не доедет, докопируем.
        # Без set -e: кривая раскладка не должна валить установку.
        srcs = ", ".join("('xkb', '%s')" % l.strip() for l in layout.split(","))
        cmds.append(
            "mkdir -p /etc/xdg /etc/skel/.config\n"
            "cat > /etc/skel/.config/kxkbrc <<'KXKBEOF'\n"
            "[Layout]\n"
            "DisplayNames=,\n"
            f"LayoutList={layout}\n"
            "Model=pc104\n"
            f"Options={opts}\n"
            "SwitchMode=Global\n"
            "Use=true\n"
            "ResetOldOptions=true\n"
            "KXKBEOF\n"
            # /etc/xdg — системный дефолт KConfig для БУДУЩИХ юзеров
            "cp -f /etc/skel/.config/kxkbrc /etc/xdg/kxkbrc || true\n"
            "for h in /home/*; do\n"
            "  [ -d \"$h\" ] || continue\n"
            "  u=$(basename \"$h\")\n"
            "  mkdir -p \"$h/.config\"\n"
            "  [ -e \"$h/.config/kxkbrc\" ] || cp /etc/skel/.config/kxkbrc \"$h/.config/kxkbrc\" || true\n"
            "  chown -R \"$u:$u\" \"$h/.config\" 2>/dev/null || true\n"
            "done\n"
            # dconf: GNOME и Cinnamon. Профиль user создаём тут же — блок
            # брендинга ниже создаёт его под тем же guard'ом, конфликта нет.
            "mkdir -p /etc/dconf/profile /etc/dconf/db/local.d\n"
            "[ -f /etc/dconf/profile/user ] || cat > /etc/dconf/profile/user <<'USRPEOF'\n"
            "user-db:user\n"
            "system-db:local\n"
            "USRPEOF\n"
            "cat > /etc/dconf/db/local.d/02-ouvert-keyboard <<'KBDEOF'\n"
            "[org/gnome/desktop/input-sources]\n"
            f"sources=[{srcs}]\n"
            f"xkb-options=['{opts}']\n"
            "\n"
            "[org/gnome/desktop/wm/keybindings]\n"
            "switch-input-source=['<Alt>Shift_L']\n"
            "switch-input-source-backward=['<Shift>Alt_L']\n"
            "\n"
            # Cinnamon форкнул гномовские схемы. Гномовские он ЧИТАЕТ, но
            # csd-keyboard применяет ИМЕННО свои (доказано на t20 27.07.26).
            # xkb-options здесь НЕ пишем: переключает кейбиндинг Muffin,
            # xkb-опция сверху дала бы двойное срабатывание Alt+Shift.
            "[org/cinnamon/desktop/input-sources]\n"
            f"sources=[{srcs}]\n"
            "\n"
            "[org/cinnamon/desktop/keybindings/wm]\n"
            "switch-input-source=['<Alt>Shift_L']\n"
            "switch-input-source-backward=['<Shift>Alt_L']\n"
            "KBDEOF\n"
            "dconf update || true\n"
            # Системный слой xkb для «голых» wayland-композиторов
            # (niri, sway, labwc, hyprland): они читают libxkbcommon и знать
            # не знают ни про dconf, ни про kxkbrc. GNOME/KDE/Cinnamon эти
            # переменные игнорируют -> двойного переключения не будет.
            "touch /etc/environment\n"
            "sed -i '/^XKB_DEFAULT_LAYOUT=/d;/^XKB_DEFAULT_OPTIONS=/d' /etc/environment || true\n"
            f"printf 'XKB_DEFAULT_LAYOUT={layout}\\nXKB_DEFAULT_OPTIONS={opts}\\n' >> /etc/environment\n"
        )

    # Чистка секции [ouvert] из pacman.conf ЦЕЛИ. Блоков там ДВА
    # (см. комментарий у CUSTOM_REPOS). Каждый — ровно 3 строки:
    #   [ouvert] / SigLevel = ... / Server = ...
    # (repositories_config(), lib/models/mirrors.py). Диапазон /re/,+2
    # sed применяет к каждому совпадению, так что уйдут оба.
    # Без этого pacman -Syu у юзера падает: file:///opt/ouvert-repo
    # после перезагрузки не существует.
    # Бонус: пакеты становятся foreign -> paru видит для них обновления
    # в AUR. Если оставить [ouvert], paru счёл бы их реповыми и не
    # обновлял бы никогда.
    cmds.append(
        "set -e\n"
        f"sed -i '/^\\[{REPO_NAME}\\]$/,+2d' /etc/pacman.conf\n"
    )

    # Flathub. Без || true падение (нет сети) уронило бы всю установку:
    # run_custom_user_commands не ловит ошибки (installer.py:2141).
    cmds.append(
        "flatpak remote-add --if-not-exists flathub "
        "https://dl.flathub.org/repo/flathub.flatpakrepo || true\n"
    )

    # DuckDuckGo как поисковик по умолчанию в Waterfox.
    # Waterfox — форк Firefox ESR: поисковик задаётся enterprise-политикой
    # (policies.json), обычные preferences его не переключают.
    # ВАЖНО: /etc/waterfox/policies/policies.json перекрывает пакетный
    # /opt/waterfox/distribution/policies.json ЦЕЛИКОМ, поэтому ключи
    # AppAutoUpdate/ManualAppUpdateOnly продублированы здесь — без них
    # Waterfox полезет обновлять сам себя в /opt и будет ругаться.
    cmds.append(
        "set -e\n"
        "mkdir -p /etc/waterfox/policies\n"
        "cat > /etc/waterfox/policies/policies.json <<'DDGEOF'\n"
        '{\n'
        '  "policies": {\n'
        '    "AppAutoUpdate": false,\n'
        '    "ManualAppUpdateOnly": true,\n'
        '    "SearchEngines": {\n'
        '      "Default": "DuckDuckGo"\n'
        '    }\n'
        '  }\n'
        '}\n'
        "DDGEOF\n"
    )

    # ===================== ЭТАП 3: БРЕНДИНГ =====================
    # Критичная часть: os-release + GRUB. set -e — если сломалось,
    # пусть падает громко, а не тихо оставляет Arch-морду.
    cmds.append(
        "set -e\n"
        # /etc/os-release на Arch — симлинк на /usr/lib/os-release
        # (пакет filesystem). Файл в /etc перекрывает /usr/lib.
        "rm -f /etc/os-release\n"
        "cat > /etc/os-release <<'OSREOF'\n"
        'NAME="Ouvert Linux"\n'
        'PRETTY_NAME="Ouvert Linux"\n'
        "ID=ouvert\n"
        "ID_LIKE=arch\n"
        "BUILD_ID=rolling\n"
        'ANSI_COLOR="38;2;46;159;240"\n'
        # LOGO — имя иконки; ouvert.png лежит в /usr/share/pixmaps
        # (пакет ouvert-branding), pixmaps — штатный fallback поиска иконок.
        "LOGO=ouvert\n"
        "OSREOF\n"
        # GRUB: имя в пунктах меню + фоновая картинка.
        "sed -i 's|^#\\?GRUB_DISTRIBUTOR=.*|GRUB_DISTRIBUTOR=\"Ouvert Linux\"|' /etc/default/grub\n"
        "grep -q '^GRUB_BACKGROUND=' /etc/default/grub"
        " && sed -i 's|^GRUB_BACKGROUND=.*|GRUB_BACKGROUND=\"/usr/share/ouvert/grub-bg.png\"|' /etc/default/grub"
        " || echo 'GRUB_BACKGROUND=\"/usr/share/ouvert/grub-bg.png\"' >> /etc/default/grub\n"
        "grep -q '^GRUB_TERMINAL_OUTPUT=' /etc/default/grub"
        " && sed -i 's|^GRUB_TERMINAL_OUTPUT=.*|GRUB_TERMINAL_OUTPUT=console|' /etc/default/grub"
        " || echo 'GRUB_TERMINAL_OUTPUT=console' >> /etc/default/grub\n"
        # bug 25: включить поиск чужих ОС (GRUB >= 2.06 выключает его по умолчанию)
        "grep -q '^GRUB_DISABLE_OS_PROBER=' /etc/default/grub"
        " && sed -i 's|^GRUB_DISABLE_OS_PROBER=.*|GRUB_DISABLE_OS_PROBER=false|' /etc/default/grub"
        " || echo 'GRUB_DISABLE_OS_PROBER=false' >> /etc/default/grub\n"
        "grub-mkconfig -o /boot/grub/grub.cfg\n"
    )

    # Косметика DE. БЕЗ set -e: обои не должны валить установку.
    # Каждый кусок за guard'ом — выполняется только если DE/механизм есть.
    cmds.append(
        # GDM: гасим лого дистрибутива на экране логина. Без явного logo GDM
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
        "cat > /etc/dconf/db/gdm.d/07-ouvert-nologo <<'GDMLEOF'\n"
        "[org/gnome/login-screen]\n"
        "logo=''\n"
        "GDMLEOF\n"
        # Обои по умолчанию GNOME + Cinnamon: системная dconf-база local.
        # /etc/dconf/profile/user по умолчанию НЕ существует — создаём,
        # иначе system-db:local никто не прочитает.
        "if command -v dconf >/dev/null 2>&1; then\n"
        "  mkdir -p /etc/dconf/profile /etc/dconf/db/local.d\n"
        "  [ -f /etc/dconf/profile/user ] || cat > /etc/dconf/profile/user <<'USRPEOF'\n"
        "user-db:user\n"
        "system-db:local\n"
        "USRPEOF\n"
        "  cat > /etc/dconf/db/local.d/01-ouvert-background <<'BGEOF'\n"
        "[org/gnome/desktop/background]\n"
        "picture-uri='file:///usr/share/wallpapers/Ouvert/ouvert.png'\n"
        "picture-uri-dark='file:///usr/share/wallpapers/Ouvert/ouvert.png'\n"
        "picture-options='zoom'\n"
        "\n"
        "[org/cinnamon/desktop/background]\n"
        "picture-uri='file:///usr/share/wallpapers/Ouvert/ouvert.png'\n"
        "BGEOF\n"
        "  dconf update || true\n"
        "fi\n"
        # XFCE: имена мониторов в xfconf заранее неизвестны (Virtual-1 в ВМ,
        # eDP-1/HDMI-1 на железе) — надёжнее подменить ДЕФОЛТНЫЕ фоны
        # xfdesktop. GdkPixbuf определяет формат по содержимому, не по
        # расширению, так что PNG под именем *.svg рендерится нормально.
        # Минус: обновление пакета xfdesktop вернёт свои файлы (известно,
        # чинится позже pacman-хуком).
        "if [ -d /usr/share/backgrounds/xfce ]; then\n"
        "  for f in /usr/share/backgrounds/xfce/*; do\n"
        "    cp -f /usr/share/wallpapers/Ouvert/ouvert.png \"$f\" || true\n"
        "  done\n"
        "fi\n"
        # KDE Plasma: те же ouvert.png (отдельные KDE-обои выброшены Патчем 60,
        # Bug 58: cp молча падал на || true). Дефолт в Plasma без правки
        # конфига под монитор не задать, поэтому подменяем содержимое
        # ДЕФОЛТНОГО набора Next (пакет plasma-workspace-wallpapers): новый
        # юзер получает Next -> видит наш фон. Есть только если KDE стоит.
        # Все разрешения + images_dark, чтобы фон был на любой теме. Проверено t14.
        "if [ -d /usr/share/wallpapers/Next/contents ]; then\n"
        "  for f in /usr/share/wallpapers/Next/contents/images/*.png /usr/share/wallpapers/Next/contents/images_dark/*.png; do\n"
        "    cp -f /usr/share/wallpapers/Ouvert/ouvert.png \"$f\" || true\n"
        "  done\n"
        "fi\n"
        # ★ Bug 47 cosmic: обои COSMIC.
        # Здесь НЕ подмена чужих файлов, как в XFCE/KDE выше, а штатный
        # оверрайд cosmic-config. Системный дефолт /usr/share/cosmic/
        # принадлежит пакету cosmic-bg — туда писать нельзя. Свои ключи
        # кладёт ouvert-branding в /etc/skel, здесь разносим их по уже
        # созданным /home/* (юзер создаётся ДО пакетов — лог t11).
        # Условие по каталогу, а не по выбору DE в GUI: юзер мог доставить
        # COSMIC вторым столом. Та же логика, что у блока Next выше.
        # Схема RON снята с живого cosmic-bg 1:1.5.0-1, не выдумана.
        "if [ -d /usr/share/cosmic ] && [ -f /etc/skel/.config/cosmic/com.system76.CosmicBackground/v1/all ]; then\n"
        "  for h in /home/*; do\n"
        "    [ -d \"$h\" ] || continue\n"
        "    u=$(basename \"$h\")\n"
        "    d=\"$h/.config/cosmic/com.system76.CosmicBackground/v1\"\n"
        "    if [ ! -e \"$d/all\" ]; then\n"
        "      mkdir -p \"$d\"\n"
        "      cp /etc/skel/.config/cosmic/com.system76.CosmicBackground/v1/all \"$d/\" || true\n"
        "      cp /etc/skel/.config/cosmic/com.system76.CosmicBackground/v1/backgrounds \"$d/\" || true\n"
        "      chown -R \"$u:$u\" \"$h/.config\" 2>/dev/null || true\n"
        "    fi\n"
        "  done\n"
        "fi\n"
        # fastfetch при открытии терминала. /etc/skel/.bashrc принадлежит
        # пакету bash — класть свой skel-файл в ouvert-branding нельзя
        # (конфликт), поэтому дописываем здесь. custom_commands выполняются
        # ПОСЛЕ создания юзера -> правим и skel (будущие юзеры), и
        # существующие /home/* (уже созданный admin).
        # Патч 2: юзер создаётся ДО установки пакетов (лог t11) ->
        # skel-файлы ouvert-branding доезжают только до БУДУЩИХ юзеров.
        # Существующим докопируем вручную (без перезаписи, вдруг юзер свой).
        "for h in /home/*; do\n"
        "  [ -d \"$h\" ] || continue\n"
        "  u=$(basename \"$h\")\n"
        "  if [ ! -e \"$h/.config/fastfetch/config.jsonc\" ]; then\n"
        "    mkdir -p \"$h/.config/fastfetch\"\n"
        "    cp /etc/skel/.config/fastfetch/config.jsonc \"$h/.config/fastfetch/\" || true\n"
        "  fi\n"
        "  chown -R \"$u:$u\" \"$h/.config\" 2>/dev/null || true\n"
        "done\n"
        "printf '\\n# Ouvert Linux\\ncommand -v fastfetch >/dev/null 2>&1 && fastfetch\\n' >> /etc/skel/.bashrc\n"
        "for h in /home/*; do\n"
        "  [ -d \"$h\" ] || continue\n"
        "  printf '\\n# Ouvert Linux\\ncommand -v fastfetch >/dev/null 2>&1 && fastfetch\\n' >> \"$h/.bashrc\"\n"
        "  chown \"$(basename \"$h\"):$(basename \"$h\")\" \"$h/.bashrc\" || true\n"
        "done\n"
    )
    # =================== КОНЕЦ ЭТАПА 3 ===================

    return cmds


def is_uefi() -> bool:
    """UEFI или Legacy BIOS. От этого зависят флаги ESP и таблица разделов."""
    return EFI_MARKER.exists()


def detect_sector_size(disk: str) -> int:
    """Логический размер сектора. Хардкод 512 врёт на 4Kn-дисках."""
    try:
        out = subprocess.run(
            ["lsblk", "-J", "-d", "-b", "-o", "PATH,LOG-SEC", disk],
            capture_output=True, text=True, timeout=10,
        ).stdout
        devs = json.loads(out).get("blockdevices", [])
        if devs:
            return int(devs[0].get("log-sec") or 512)
    except Exception:
        pass
    return 512


def list_partitions(disk: str) -> list[dict]:
    """Существующие разделы диска для ручного режима.

    START — смещение в 512-байтных секторах (sysfs), всегда 512, независимо
    от LOG-SEC. Поэтому start_bytes = START * 512.
    """
    try:
        out = subprocess.run(
            ["lsblk", "-J", "-b", "-o", "PATH,SIZE,START,FSTYPE,FSVER,TYPE,PARTTYPENAME", disk],
            capture_output=True, text=True, timeout=10,
        ).stdout
        tree = json.loads(out).get("blockdevices", [])
    except Exception:
        return []

    parts: list[dict] = []

    def walk(nodes):
        for n in nodes:
            if n.get("type") == "part":
                parts.append({
                    "path": n.get("path"),
                    "size": int(n.get("size") or 0),
                    "start": int(n.get("start") or 0) * 512,
                    "cur_fs": map_lsblk_fs(n.get("fstype") or "", n.get("fsver") or ""),
                    "raw_fs": (n.get("fstype") or "").strip(),  # только для показа юзеру
                    "parttype": (n.get("parttypename") or "").strip(),
                    "mountpoint": None,
                    "format": False,
                    "fs": "ext4",
                })
            walk(n.get("children") or [])

    walk(tree)
    return parts


# --- примитивы JSON ---

def _sector(state: dict) -> dict:
    return {"value": int(state.get("sector_size") or 512), "unit": "B"}


def _size(state: dict, unit: str, value: int) -> dict:
    return {"value": int(value), "unit": unit, "sector_size": _sector(state)}


def _part(state: dict, **kw) -> dict:
    p = {
        "obj_id": str(uuid.uuid4()),
        "status": "create",
        "type": "primary",
        "fs_type": None,
        "mountpoint": None,
        "flags": [],
        "dev_path": None,
        "btrfs": [],
        "mount_options": [],
        "start": _size(state, "MiB", FIRST_START_MIB),
        "size": _size(state, "MiB", 1),
    }
    p.update(kw)
    return p


def _mount_options(state: dict) -> list[str]:
    if state.get("fs") == "btrfs" and state.get("btrfs_compress", True):
        return ["compress=zstd"]  # BtrfsMountOption.compress
    return []


def use_subvols(state: dict) -> bool:
    return state.get("fs") == "btrfs" and bool(state.get("btrfs_subvols", True))


def use_separate_home(state: dict) -> bool:
    # archinstall сам исключает /home при сабволюмах — @home их заменяет
    return bool(state.get("separate_home")) and not use_subvols(state)


def available_mib(state: dict) -> int:
    """Полезное место с учётом резерва под backup-заголовок GPT."""
    total_mib = int(state.get("disk_size") or 0) // MIB
    return total_mib - 1 if is_uefi() else total_mib


def max_root_gib(state: dict) -> int:
    """Максимум под корень, когда /home отдельным разделом (мин. 8 GiB под /home)."""
    return max(1, (available_mib(state) - ROOT_START_MIB - 8 * 1024) // 1024)


# --- режим «Стереть диск» ---

def _wipe_partitions(state: dict) -> list[dict]:
    uefi = is_uefi()
    avail_mib = available_mib(state)
    fs = state.get("fs") or "ext4"
    subvols = use_subvols(state)
    sep_home = use_separate_home(state)

    # _boot_partition() из archinstall: fat32, /boot, 1 GiB, старт 1 MiB,
    # флаг esp добавляется ТОЛЬКО при GPT (то есть при UEFI). Баг 6: без esp
    # is_efi() не находит раздел -> "Could not detect efi partition".
    boot = _part(
        state,
        fs_type="fat32",
        mountpoint="/boot",
        flags=["boot", "esp"] if uefi else ["boot"],
        start=_size(state, "MiB", FIRST_START_MIB),
        size=_size(state, "MiB", ESP_MIB),
    )

    if sep_home:
        root_mib = int(state.get("root_size_gib") or 40) * 1024
    else:
        root_mib = avail_mib - ROOT_START_MIB
    root_mib = max(root_mib, 1)

    root = _part(
        state,
        fs_type=fs,
        mountpoint=None if subvols else "/",
        btrfs=list(DEFAULT_SUBVOLS) if subvols else [],
        mount_options=_mount_options(state),
        start=_size(state, "MiB", ROOT_START_MIB),
        size=_size(state, "MiB", root_mib),
    )

    parts = [boot, root]

    if sep_home:
        home_start = ROOT_START_MIB + root_mib
        home_mib = max(avail_mib - home_start, 1)
        parts.append(_part(
            state,
            fs_type=fs,
            mountpoint="/home",
            flags=["linux-home"] if uefi else [],  # флаг только для GPT
            mount_options=_mount_options(state),
            start=_size(state, "MiB", home_start),
            size=_size(state, "MiB", home_mib),
        ))

    return parts


# --- режим «Вручную» ---

def _manual_partitions(state: dict) -> list[dict]:
    """Существующие разделы. status:
         existing — примонтировать как есть, НЕ форматировать
         modify   — отформатировать (filesystem.py: create+modify)
       dev_path обязателен для обоих, fs_type обязателен для modify.
       Разделы без точки монтирования в конфиг не попадают вообще.
    """
    uefi = is_uefi()
    parts_in = state.get("manual_parts") or []
    # Отдельный ESP (/efi) -> /boot становится обычным ext4 под ядро,
    # а сам ESP несёт ТОЛЬКО esp. Для dual-boot с чужим ~100-МиБ ESP (Bug 19).
    has_separate_esp = uefi and any(p.get("mountpoint") == "/efi" for p in parts_in)
    out: list[dict] = []
    for p in parts_in:
        mp = p.get("mountpoint")
        if not mp:
            continue

        fmt = bool(p.get("format"))
        flags: list[str] = []

        if mp == "swap":
            fs_type = "linux-swap"
            mountpoint = None
            flags = ["swap"]
        elif mp == "/efi":
            # Отдельный ESP (dual-boot). ТОЛЬКО esp: дать ему boot нельзя —
            # get_boot_partition() выберет ESP, --boot-directory уедет на
            # 100-МиБ раздел и ядро снова не влезет (Bug 19). FAT32
            # обязателен: прошивка читает ФС, а не только флаг.
            fs_type = "fat32" if fmt else (p.get("cur_fs") or "fat32")
            mountpoint = mp
            flags = ["esp"] if uefi else ["boot"]
        elif mp == "/boot":
            fs_type = (p.get("fs") if fmt else p.get("cur_fs")) or "ext4"
            mountpoint = mp
            if has_separate_esp:
                # /boot — обычный ext4 под ядро+initramfs (ESP отдельно)
                flags = ["boot"]
            elif uefi:
                # Классика: /boot САМ является ESP -> boot+esp, FAT32
                if fmt:
                    fs_type = "fat32"
                flags = ["boot", "esp"]
            else:
                flags = ["boot"]
        else:
            fs_type = (p.get("fs") if fmt else p.get("cur_fs")) or "ext4"
            mountpoint = mp

        out.append(_part(
            state,
            status="modify" if fmt else "existing",
            fs_type=fs_type,
            mountpoint=mountpoint,
            dev_path=p["path"],
            flags=flags,
            mount_options=["compress=zstd"] if (fmt and fs_type == "btrfs") else [],
            start=_size(state, "B", int(p.get("start") or 0)),
            size=_size(state, "B", int(p.get("size") or 0)),
        ))

    return out


# --- сборка disk_config ---

def build_disk_config(state: dict) -> dict:
    if state.get("part_mode") == "manual":
        return {
            "config_type": "manual_partitioning",
            "device_modifications": [{
                "device": state["disk"],
                "wipe": False,
                "partitions": _manual_partitions(state),
            }],
        }

    parts = _wipe_partitions(state)
    cfg = {
        "config_type": "default_layout",
        "device_modifications": [{
            "device": state["disk"],
            "wipe": True,
            "partitions": parts,
        }],
    }

    if state.get("luks") and state.get("luks_password"):
        # Шифруем всё, кроме /boot. Для /home archinstall сам сгенерит keyfile,
        # корень спросит пароль на загрузке (хуки encrypt + cryptdevice=... —
        # installer.py делает это сам).
        enc = [p["obj_id"] for p in parts if p["mountpoint"] != "/boot"]
        cfg["disk_encryption"] = {
            "encryption_type": "luks",
            "partitions": enc,
            "lvm_volumes": [],
        }

    return cfg


# ── ЭТАП 2Б: РЕПОЗИТОРИЙ OUVERT И ПРЕДУСТАНОВКА ──────────────────────
#
# Репозиторий едет в ISO (build.sh кладёт его в airootfs/opt/ouvert-repo),
# поэтому в ЖИВОЙ системе он доступен как обычный каталог.
#
# Как это работает (проверено по исходникам archinstall 4.4):
#   guided.py:101  set_mirrors(on_target=False) -> дописывает [ouvert]
#                  в pacman.conf ЖИВОЙ системы;
#   pacman.py:111  pacstrap -C /etc/pacman.conf -> ВСЕГДА конфиг живой
#                  системы, и для base, и для add_additional_packages,
#                  значит наши пакеты видны;
#   installer.py:953 PacmanConfig.persist() -> КОПИРУЕТ живой pacman.conf
#                  в цель целиком (вместе с [ouvert]);
#   guided.py:112  set_mirrors(on_target=True) -> дописывает [ouvert]
#                  в цель ВТОРОЙ раз.
# Итог: в целевом pacman.conf два блока [ouvert] с путём file:///opt/...,
# которого после перезагрузки не существует. Поэтому build_custom_commands
# ОБЯЗАН вычистить секцию — иначе у юзера падает pacman -Syu.
REPO_NAME = "ouvert"
REPO_DIR = "/opt/ouvert-repo/x86_64"
REPO_URL = f"file://{REPO_DIR}"

# Пакеты не подписаны -> SigLevel = Never TrustAll.
# Значения строгие, это энумы SignCheck/SignOption (lib/models/mirrors.py).
CUSTOM_REPOS = [
    {
        "name": REPO_NAME,
        "url": REPO_URL,
        "sign_check": "Never",
        "sign_option": "TrustAll",
    }
]

# Предустановка. Из нашего репо приедут и зависимости (python-steam и др.).
PACKAGES = [
    # наш репозиторий
    "waterfox-bin",  # AUR, epoch 1; conflicts=('waterfox'), ставит /opt/waterfox
    "protonup-qt",
    "paru",
    "ouvert-branding",  # этап 3: обои, лого, конфиг fastfetch
    "os-prober",  # bug 25: обнаружение второй ОС (Windows) для меню GRUB
    # официальные репозитории
    "kitty",
    "kate",
    "fastfetch",
    "cmatrix",
    "cava",
    "git",
    "base-devel",  # Bug 61: без него paru не собирает AUR (нет fakeroot)
    "flatpak",
    "dconf",  # чтобы dconf update скомпилил заглушку gdm-лого даже без gdm
]

# Требуют multilib. Если юзер снял галку — steam просто не поставится,
# а установка упала бы целиком на "target not found".
PACKAGES_MULTILIB = ["steam"]


def build_packages(state: dict) -> list[str]:
    pkgs = list(PACKAGES)
    if "multilib" in (state.get("repos") or []):
        pkgs += PACKAGES_MULTILIB
    return pkgs


def build_config(state: dict) -> dict:
    ru = state.get("lang") == "ru"
    profile = state["profile"]

    return {
        "version": "4.4",
        "archinstall-language": "English",
        "hostname": state.get("hostname") or "ouvert",
        "kernels": KERNEL_SETS.get(state.get("kernel") or "ouvert", ["linux-ouvert"]),
        # removable=True — fallback /EFI/BOOT/BOOTX64.EFI. Баг 7: без него
        # система не грузится после сброса NVRAM. В v3 стояло False.
        "bootloader_config": {"bootloader": "Grub", "uki": False, "removable": True},
        "disk_config": build_disk_config(state),
        "locale_config": {
            "kb_layout": KB_LAYOUTS.get(state.get("kb") or "us", KB_LAYOUTS["us"])["kb_layout"],
            "sys_enc": "UTF-8",
            "sys_lang": "ru_RU" if ru else "en_US",
            "console_font": pick_console_font(state.get("lang") or "en"),
        },
        "network_config": {"type": "nm"},
        "app_config": {
            "audio_config": {"audio": "pipewire"},
            "bluetooth_config": {"enabled": True},
            "print_service_config": {"enabled": True},
        },
        "mirror_config": {
            "optional_repositories": state.get("repos") or [],
            "custom_repositories": CUSTOM_REPOS,
        },
        "profile_config": {
            "gfx_driver": state.get("gfx") or "All open-source",
            "greeter": state["greeter"],
            "profile": {
                "main": "Desktop",
                "details": [profile],
                "custom_settings": CUSTOM_SETTINGS.get(profile, {}),
            },
        },
        "swap": {"enabled": True, "algorithm": "zstd"},
        "ntp": True,
        "timezone": state.get("timezone") or ("Europe/Moscow" if ru else "UTC"),
        "packages": build_packages(state),
        "custom_commands": build_custom_commands(state),
        "pacman_config": {"color": True, "parallel_downloads": 5},
        "script": "guided",
    }


def build_creds(state: dict) -> dict:
    creds: dict = {
        "users": [
            {
                "username": state["username"],
                "!password": state["password"],
                "sudo": True,
            }
        ]
    }
    # args.py: config.update(creds) — ключ читается из общего словаря.
    # Без пароля DiskEncryption.parse_arg молча вернёт None (шифрования не будет).
    if state.get("part_mode") != "manual" and state.get("luks") and state.get("luks_password"):
        creds["encryption_password"] = state["luks_password"]
    return creds


def write_configs(state: dict) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(build_config(state), indent=2, ensure_ascii=False))
    CREDS_PATH.write_text(json.dumps(build_creds(state), indent=2, ensure_ascii=False))
    os.chmod(CREDS_PATH, 0o600)
    return CONFIG_PATH, CREDS_PATH
