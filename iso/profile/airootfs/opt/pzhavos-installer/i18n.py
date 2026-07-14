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
    "tz_region": {"ru": "Регион", "en": "Region"},
    "tz_city": {"ru": "Город", "en": "City"},

    "disk_title": {"ru": "Куда ставим систему?", "en": "Where do we install?"},
    "disk_warn": {"ru": "Выбранный диск будет полностью стёрт!", "en": "The selected disk will be completely erased!"},
    "refresh": {"ru": "Обновить", "en": "Refresh"},
    "no_disks": {"ru": "Диски не найдены. Подключи диск и нажми «Обновить».", "en": "No disks found. Attach a disk and press Refresh."},

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
