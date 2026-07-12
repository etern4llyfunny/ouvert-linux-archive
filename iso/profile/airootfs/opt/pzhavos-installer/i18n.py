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

    "disk_title": {"ru": "Разметка диска", "en": "Disk layout"},
    "disk_stub": {
        "ru": "Здесь будет выбор диска и авторазметка через archinstall.",
        "en": "Disk selection and auto-layout via archinstall will be here.",
    },

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
    "not_set": {"ru": "не задано", "en": "not set"},
    "install_stub": {
        "ru": "Установка появится, когда подключим archinstall как библиотеку.",
        "en": "Installation will work once archinstall is wired in as a library.",
    },
}


def tr(key: str) -> str:
    return STRINGS.get(key, {}).get(_LANG, key)


def set_lang(lang: str) -> None:
    global _LANG
    _LANG = lang


def current_lang() -> str:
    return _LANG
