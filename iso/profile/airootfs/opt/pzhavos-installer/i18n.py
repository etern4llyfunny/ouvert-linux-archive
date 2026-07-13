"""Локализация. Пока простой словарь, при росте переедем на gettext."""

_LANG = "ru"

STRINGS = {
    "app_title": {"ru": "Установщик PzhavOS", "en": "PzhavOS Installer"},
    "back": {"ru": "Назад", "en": "Back"},
    "next": {"ru": "Далее", "en": "Next"},
    "install": {"ru": "Установить", "en": "Install"},
    "step": {"ru": "Шаг", "en": "Step"},
    "stub_notice": {"ru": "Заглушка — реализуем в следующих сессиях.", "en": "Stub — coming in next sessions."},

    "welcome_title": {"ru": "Добро пожаловать в установщик PzhavOS!", "en": "Welcome to the PzhavOS installer!"},
    "welcome_text": {
        "ru": "Пара простых шагов — и система готова.\nВыбери язык установки:",
        "en": "A few simple steps and your system is ready.\nChoose the installer language:",
    },

    "network_title": {"ru": "Подключение к сети", "en": "Network connection"},
    "network_stub": {
        "ru": "Здесь будет список Wi-Fi сетей (NetworkManager) и статус подключения.\nКабель по DHCP подключается автоматически.",
        "en": "Wi-Fi network list (NetworkManager) and connection status will be here.\nEthernet via DHCP connects automatically.",
    },

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

    "summary_title": {"ru": "Сводка перед установкой", "en": "Summary"},
    "lang_label": {"ru": "Язык", "en": "Language"},
    "desktop_label": {"ru": "Окружение", "en": "Desktop"},
    "disk_label": {"ru": "Диск", "en": "Disk"},
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
