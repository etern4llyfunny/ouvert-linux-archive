"""Локализация. Пока простой словарь, при росте переедем на gettext."""

_LANG = "ru"

STRINGS = {
    "app_title": {"ru": "Установщик PzhavOS", "en": "PzhavOS Installer"},
    "back": {"ru": "Назад", "en": "Back"},
    "next": {"ru": "Далее", "en": "Next"},
    "install": {"ru": "Установить", "en": "Install"},
    "step": {"ru": "Шаг", "en": "Step"},

    "welcome_title": {"ru": "Добро пожаловать в установщик PzhavOS!", "en": "Welcome to the PzhavOS installer!"},
    "welcome_text": {
        "ru": "Пара простых шагов — и система готова.\nВыбери язык установки:",
        "en": "A few simple steps and your system is ready.\nChoose the installer language:",
    },

    "network_title": {"ru": "Подключение к интернету", "en": "Internet connection"},
    "net_type": {"ru": "Как подключаемся?", "en": "How do you connect?"},
    "net_wired": {"ru": "Проводное (кабель)", "en": "Wired (cable)"},
    "net_wifi": {"ru": "Wi-Fi", "en": "Wi-Fi"},
    "net_check": {"ru": "Проверить", "en": "Check"},
    "net_checking": {"ru": "Проверяю соединение…", "en": "Checking connection…"},
    "net_ok_msg": {"ru": "Интернет есть, можно продолжать.", "en": "Internet is up, you can continue."},
    "net_fail": {"ru": "Нет соединения. Проверь кабель или подключись к Wi-Fi.", "en": "No connection. Check the cable or connect to Wi-Fi."},
    "net_iface": {"ru": "Wi-Fi адаптер", "en": "Wi-Fi adapter"},
    "net_no_iface": {"ru": "Wi-Fi адаптеров не найдено.", "en": "No Wi-Fi adapters found."},
    "net_ssid": {"ru": "Сеть", "en": "Network"},
    "net_scan": {"ru": "Сканировать", "en": "Scan"},
    "net_pass": {"ru": "Пароль сети", "en": "Network password"},
    "net_connect": {"ru": "Подключиться", "en": "Connect"},
    "net_connecting": {"ru": "Подключаюсь…", "en": "Connecting…"},
    "net_host_only": {"ru": "Wi-Fi доступен только при запуске с ISO.", "en": "Wi-Fi is only available when running from the ISO."},
    "err_no_net": {"ru": "Сначала подключись к интернету — без него установка не пройдёт.", "en": "Connect to the internet first — installation needs it."},

    "tz_title": {"ru": "Регион и время", "en": "Region & time"},
    "region_title": {"ru": "Регион, время и клавиатура", "en": "Region, time & keyboard"},
    "kb_label": {"ru": "Раскладка", "en": "Keyboard layout"},
    "kb_us_ru": {"ru": "Русская + английская (Alt+Shift)", "en": "Russian + English (Alt+Shift)"},
    "kb_us": {"ru": "Только английская (US)", "en": "English only (US)"},
    "kb_ru": {"ru": "Только русская", "en": "Russian only"},
    "kb_console": {"ru": "В консоли (TTY)", "en": "In console (TTY)"},
    "kb_note_us_ru": {
        "ru": "Переключение Alt+Shift в графике. В консоли остаётся английская —\nчтобы логин и пароль всегда можно было набрать.",
        "en": "Alt+Shift toggles in the desktop. The console stays English,\nso login and password can always be typed.",
    },
    "kb_note_single": {
        "ru": "Одна раскладка везде: и в графике, и в консоли.",
        "en": "One layout everywhere: desktop and console.",
    },
    "tz_region": {"ru": "Регион", "en": "Region"},
    "tz_city": {"ru": "Город", "en": "City"},

    "disk_title": {"ru": "Куда ставим систему?", "en": "Where do we install?"},
    "disk_warn": {
        "ru": "Что делать с диском — выберешь на следующем шаге.",
        "en": "What to do with the disk is decided on the next step.",
    },
    "refresh": {"ru": "Обновить", "en": "Refresh"},
    "no_disks": {"ru": "Диски не найдены. Подключи диск и нажми «Обновить».", "en": "No disks found. Attach a disk and press Refresh."},

    # --- v4: разметка ---
    "part_title": {"ru": "Разметка диска", "en": "Disk partitioning"},
    "part_mode_wipe": {"ru": "Стереть диск", "en": "Erase disk"},
    "part_mode_manual": {"ru": "Вручную", "en": "Manual"},
    "part_fs": {"ru": "Файловая система", "en": "Filesystem"},
    "part_subvols": {
        "ru": "Сабволюмы btrfs (@, @home, @log, @pkg) — нужны для снапшотов",
        "en": "Btrfs subvolumes (@, @home, @log, @pkg) — needed for snapshots",
    },
    "part_compress": {"ru": "Сжатие zstd", "en": "zstd compression"},
    "part_sep_home": {"ru": "Отдельный раздел /home", "en": "Separate /home partition"},
    "part_root_size": {"ru": "Размер корня", "en": "Root size"},
    "part_luks": {"ru": "Шифровать диск (LUKS)", "en": "Encrypt disk (LUKS)"},
    "part_luks_pass": {"ru": "Пароль шифрования", "en": "Encryption password"},
    "part_luks_pass2": {"ru": "Повтор пароля", "en": "Repeat password"},
    "part_luks_note": {
        "ru": "Пароль спрашивается при каждой загрузке, ДО входа в систему.\nЗабудешь — данные не восстановить никак.",
        "en": "The password is asked at every boot, before login.\nIf you forget it, the data is gone for good.",
    },
    "part_manual_hint": {
        "ru": "Разделы создай заранее (gparted). Здесь только назначь точки монтирования.\n«/» обязателен, «/boot» тоже. Без галки «Форматировать» данные раздела сохранятся.",
        "en": "Create partitions beforehand (gparted). Here you only assign mountpoints.\n“/” is required, “/boot” too. Without “Format”, the partition data is kept.",
    },
    "part_no_parts": {
        "ru": "На диске нет разделов. Создай их в gparted или выбери «Стереть диск».",
        "en": "No partitions on this disk. Create them in gparted or pick “Erase disk”.",
    },
    "part_col_format": {"ru": "Форматировать", "en": "Format"},
    "part_mount_none": {"ru": "— не трогать", "en": "— leave alone"},
    "part_wipe_warn": {
        "ru": "БУДЕТ СТЁРТО ВСЁ на диске",
        "en": "EVERYTHING will be erased on",
    },
    "part_summary": {"ru": "Что будет сделано:", "en": "What will happen:"},
    "part_will_format": {"ru": "форматировать", "en": "format"},
    "part_will_keep": {"ru": "сохранить", "en": "keep"},
    "part_label": {"ru": "Разметка", "en": "Partitioning"},
    "part_count": {"ru": "разд.", "en": "part."},

    "user_title": {"ru": "Создание пользователя", "en": "Create your user"},
    "username": {"ru": "Имя пользователя", "en": "Username"},
    "password": {"ru": "Пароль", "en": "Password"},
    "password2": {"ru": "Повтор пароля", "en": "Repeat password"},
    "hostname": {"ru": "Имя компьютера", "en": "Hostname"},

    "desktop_title": {"ru": "Выбор рабочего окружения", "en": "Choose your desktop"},
    "de_group": {"ru": "Рабочие столы", "en": "Desktop environments"},
    "wm_group": {"ru": "Оконные менеджеры (для продвинутых)", "en": "Window managers (advanced)"},

    "gfx_title": {"ru": "Видеодрайвер", "en": "Graphics driver"},
    "gfx_hint": {
        "ru": "Не уверен — оставь «All open-source».\nNvidia GTX 16xx / RTX — бери «open kernel module».\nДля виртуалки подойдёт «All open-source» или «VirtualBox».",
        "en": "Not sure — keep “All open-source”.\nNvidia GTX 16xx / RTX — pick “open kernel module”.\nIn a VM, “All open-source” or “VirtualBox” both work.",
    },

    "repo_title": {"ru": "Дополнительные репозитории", "en": "Additional repositories"},
    "adv_title": {"ru": "Ядро и репозитории", "en": "Kernel & repositories"},
    "kern_label": {"ru": "Ядро Linux", "en": "Linux kernel"},
    "kern_linux": {"ru": "linux — обычное, свежее", "en": "linux — regular, latest"},
    "kern_both": {"ru": "linux + linux-lts — запасное в меню GRUB", "en": "linux + linux-lts — fallback in GRUB menu"},
    "kern_lts": {"ru": "linux-lts — долгоживущее, для старого железа", "en": "linux-lts — long-term, for older hardware"},
    "kern_zen": {"ru": "linux-zen — отзывчивее, но капризнее", "en": "linux-zen — snappier, but fussier"},
    "kern_note": {
        "ru": "Не уверен — оставь обычное. «linux + linux-lts» даёт второй пункт\nв меню загрузки: если новое ядро сломается, загрузишься со старого.",
        "en": "Not sure — keep the regular one. “linux + linux-lts” adds a second\nboot menu entry: if the new kernel breaks, boot the old one.",
    },
    "kern_pkgs": {"ru": "Пакеты", "en": "Packages"},
    "repo_multilib_note": {
        "ru": "multilib нужен для Steam и 32-битных игр — не выключай без причины.",
        "en": "multilib is required for Steam and 32-bit games — keep it on.",
    },
    "repo_testing_warn": {
        "ru": "testing-репозитории нестабильны, новичкам не советую.",
        "en": "testing repositories are unstable, not recommended for beginners.",
    },

    "summary_title": {"ru": "Сводка перед установкой", "en": "Summary"},
    "lang_label": {"ru": "Язык", "en": "Language"},
    "desktop_label": {"ru": "Окружение", "en": "Desktop"},
    "disk_label": {"ru": "Диск", "en": "Disk"},
    "tz_label": {"ru": "Часовой пояс", "en": "Timezone"},
    "gfx_label": {"ru": "Видеодрайвер", "en": "GPU driver"},
    "repos_label": {"ru": "Доп. репозитории", "en": "Extra repos"},
    "not_set": {"ru": "не задано", "en": "not set"},

    "err_no_disk": {"ru": "Выбери диск для установки.", "en": "Select a disk to install to."},
    "err_user": {"ru": "Заполни имя пользователя и пароль.", "en": "Fill in username and password."},
    "err_pass": {"ru": "Пароли не совпадают.", "en": "Passwords do not match."},
    "err_no_root": {
        "ru": "Назначь раздел под корень «/» — без него ставить некуда.",
        "en": "Assign a partition to root “/” — there is nowhere to install otherwise.",
    },
    "err_no_boot": {
        "ru": "Назначь раздел под «/boot» — без него не встанет загрузчик.",
        "en": "Assign a partition to “/boot” — the bootloader needs it.",
    },
    "err_dup_mount": {
        "ru": "Одна точка монтирования назначена дважды.",
        "en": "The same mountpoint is assigned twice.",
    },
    "err_disk_small": {
        "ru": "Диск слишком мал: нужно минимум ~10 GiB.",
        "en": "Disk is too small: about 10 GiB minimum is needed.",
    },
    "err_root_size": {
        "ru": "Корень слишком большой — под /home не остаётся места.",
        "en": "Root is too large — no space left for /home.",
    },
    "err_luks_empty": {"ru": "Введи пароль шифрования.", "en": "Enter the encryption password."},
    "err_luks_pass": {"ru": "Пароли шифрования не совпадают.", "en": "Encryption passwords do not match."},
    "not_live": {
        "ru": "Установка запускается только с загрузочного ISO.\nКонфиги записаны в /tmp/pzhavos для проверки.",
        "en": "Installation only runs from the live ISO.\nConfigs written to /tmp/pzhavos for review.",
    },

    "progress_title": {"ru": "Установка", "en": "Installing"},
    "progress_running": {"ru": "Идёт установка, не выключай компьютер…", "en": "Installing, do not power off…"},
    "progress_done": {"ru": "Готово! Установка завершена.", "en": "Done! Installation complete."},
    "progress_fail": {"ru": "Установка завершилась с ошибкой. Лог ниже и в /tmp/pzhavos/install.log", "en": "Installation failed. Log below and in /tmp/pzhavos/install.log"},
    "reboot": {"ru": "Перезагрузить", "en": "Reboot"},
}


def tr(key: str) -> str:
    return STRINGS.get(key, {}).get(_LANG, key)


def set_lang(lang: str) -> None:
    global _LANG
    _LANG = lang


def current_lang() -> str:
    return _LANG
