"""Локализация. Пока простой словарь, при росте переедем на gettext."""

_LANG = "ru"

STRINGS = {
    "app_title": {"ru": "Установщик Ouvert Linux", "en": "Ouvert Linux Installer"},
    "back": {"ru": "Назад", "en": "Back"},
    "next": {"ru": "Далее", "en": "Next"},
    "install": {"ru": "Установить", "en": "Install"},
    "step": {"ru": "Шаг", "en": "Step"},

    # --- Патч 62: закрытие окна ---
    "close_ask": {"ru": "Выйти из установщика? Система не будет установлена.",
                  "en": "Quit the installer? The system will not be installed."},
    "close_yes": {"ru": "Выйти", "en": "Quit"},
    "close_busy": {
        "ru": "Идёт установка — закрыть установщик сейчас нельзя.\n"
              "Прерванная установка оставит диск наполовину размеченным.",
        "en": "Installation is running — the installer cannot be closed now.\n"
              "An interrupted install leaves the disk half-partitioned.",
    },

    "welcome_title": {"ru": "Добро пожаловать в установщик Ouvert Linux!", "en": "Welcome to the Ouvert Linux installer!"},
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
    "tz_pick_region": {"ru": "Выберите регион", "en": "Select region"},
    "tz_pick_city": {"ru": "Выберите город", "en": "Select city"},
    "err_no_tz": {"ru": "Выбери регион и город.", "en": "Select region and city."},

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
        "ru": "Назначь точки монтирования. «/» обязателен, «/boot» тоже.\nБез галки «Форматировать» данные раздела сохранятся. Создать или удалить раздел — кнопка «Изменить разделы…».",
        "en": "Assign the mountpoints. “/” is required, “/boot” too.\nWithout “Format” the partition data is kept. To add or remove partitions use “Edit partitions…”.",
    },
    "part_no_parts": {
        "ru": "На диске нет разделов. Создай их кнопкой «Изменить разделы…» или выбери «Стереть диск».",
        "en": "No partitions on this disk. Create them with “Edit partitions…” or pick “Erase disk”.",
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

    # --- этап 5: редактор разделов ---
    "part_edit_btn": {"ru": "Изменить разделы…", "en": "Edit partitions…"},
    "pe_title": {"ru": "Разделы диска %s", "en": "Partitions of %s"},
    "pe_hint": {
        "ru": "Что уже есть на диске. Красным помечено то, что удалять нельзя:\n"
              "загрузчик Windows, служебные разделы и разделы восстановления.\n"
              "Выбери строку — снизу будет написано, что с ней можно сделать.",
        "en": "What is already on the disk. Red marks what must not be deleted:\n"
              "the Windows bootloader, service and recovery partitions.\n"
              "Select a row — the line below tells you what you can do with it.",
    },
    "pe_stand": {
        "ru": "СТЕНД: данные из файла %s, а НЕ с реального диска",
        "en": "TEST DATA: read from %s, NOT from a real disk",
    },
    "pe_col_num": {"ru": "№", "en": "#"},
    "pe_col_start": {"ru": "Начало", "en": "Start"},
    "pe_col_size": {"ru": "Размер", "en": "Size"},
    "pe_col_fs": {"ru": "ФС", "en": "FS"},
    "pe_col_name": {"ru": "Метка", "en": "Label"},
    "pe_col_flags": {"ru": "Флаги", "en": "Flags"},
    "pe_col_what": {"ru": "Что это", "en": "What it is"},
    "pe_delete": {"ru": "Удалить раздел", "en": "Delete partition"},
    "pe_create": {"ru": "Создать раздел", "en": "Create partition"},
    "pe_close": {"ru": "Закрыть", "en": "Close"},
    "pe_soon": {"ru": "Появится в следующей версии", "en": "Coming in the next version"},
    "pe_select": {
        "ru": "Выбери строку — покажу, можно ли её удалить.",
        "en": "Select a row — I will tell you whether it can be deleted.",
    },
    "pe_can_delete": {"ru": "Этот раздел удалить можно.", "en": "This partition can be deleted."},
    "pe_cant_delete": {"ru": "Удалять нельзя: %s", "en": "Cannot delete: %s"},
    "pe_mounted": {"ru": "примонтирован: %s", "en": "mounted at: %s"},
    "pe_no_data": {
        "ru": "Не удалось прочитать таблицу разделов.\n"
              "Обычно это нехватка прав: parted требует root.",
        "en": "Could not read the partition table.\n"
              "Usually a permissions issue: parted needs root.",
    },

    # --- сессия 4: запись на диск ---
    "pe_ro": {"ru": "Изменять разделы нельзя: %s", "en": "Editing is not possible: %s"},
    # --- сессия 6: Bug 42, диск без таблицы разделов ---
    "pe_mklabel_btn": {"ru": "Создать таблицу разделов",
                       "en": "Create partition table"},
    "pe_nolabel": {
        "ru": "На диске %s нет таблицы разделов — он совершенно пустой.\n"
              "Нажми «Создать таблицу разделов», и появится место "
              "под первый раздел.",
        "en": "Disk %s has no partition table — it is completely blank.\n"
              "Press “Create partition table” to get free space "
              "for the first partition.",
    },
    "pe_hint_nolabel": {
        "ru": "Диск пустой: на нём нет даже таблицы разделов.\n"
              "Её надо создать один раз, после этого можно будет "
              "добавлять разделы.",
        "en": "The disk is blank: it has no partition table at all.\n"
              "Create it once, then you can add partitions.",
    },
    "pe_hint_empty": {
        "ru": "Таблица разделов есть, разделов пока нет.\n"
              "Выбери строку со свободным местом и нажми "
              "«Создать раздел».",
        "en": "The partition table exists, there are no partitions yet.\n"
              "Select the free space row and press “Create partition”.",
    },
    "pe_mklabel_title": {"ru": "Создать таблицу разделов?",
                         "en": "Create partition table?"},
    "pe_mklabel_text": {
        "ru": "На диске %s будет создана таблица разделов %s.\n\n"
              "Диск сейчас пуст, терять на нём нечего — данные "
              "не пострадают.",
        "en": "A partition table will be created on %s: %s.\n\n"
              "The disk is empty, there is nothing to lose — "
              "no data will be harmed.",
    },
    "pe_mklabel_yes": {"ru": "Создать", "en": "Create"},

    # --- сессия 6: Bug 45 и Bug 46, метка "loop": ФС прямо на устройстве ---
    "pe_nolabel_fs": {
        "ru": "На диске %s нет таблицы разделов, но есть файловая система "
              "%s — она занимает весь диск целиком.\n"
              "Чтобы поставить сюда систему, нужна таблица разделов, "
              "и все данные с диска при этом пропадут.",
        "en": "Disk %s has no partition table, but it does hold a %s "
              "filesystem spanning the whole device.\n"
              "Installing here needs a partition table, and creating one "
              "will destroy everything on the disk.",
    },
    "pe_hint_nolabel_fs": {
        "ru": "На этом диске нет таблицы разделов: файловая система "
              "записана прямо на устройство.\n"
              "Так бывает у флешек и внешних дисков. Разделов тут нет "
              "и не будет, пока не создана таблица.",
        "en": "This disk has no partition table: the filesystem is written "
              "straight onto the device.\n"
              "Common for flash drives and external disks. It has no "
              "partitions and cannot have any until a table is created.",
    },
    "pe_mklabel_text_fs": {
        "ru": "На диске %s будет создана таблица разделов %s.\n\n"
              "ВНИМАНИЕ: сейчас на диске лежит файловая система %s, "
              "записанная прямо на устройство. Все данные на ней "
              "пропадут безвозвратно.\n\n"
              "Если там есть что-то нужное — нажми «Отмена» и сначала "
              "скопируй файлы в другое место.",
        "en": "A partition table will be created on %s: %s.\n\n"
              "WARNING: the disk currently holds a %s filesystem written "
              "straight onto the device. All data on it will be lost "
              "for good.\n\n"
              "If anything there matters, press \u201cCancel\u201d and copy "
              "the files elsewhere first.",
    },
    "pe_pick_part": {"ru": "Сначала выбери раздел в таблице.", "en": "Select a partition first."},
    "pe_pick_free": {"ru": "Сначала выбери свободное место (бирюзовая строка).",
                     "en": "Select free space first (the teal row)."},
    "pe_can_create": {"ru": "Здесь можно создать раздел.",
                      "en": "You can create a partition here."},
    "pe_confirm_title": {"ru": "Удалить раздел?", "en": "Delete partition?"},
    "pe_confirm_text": {
        "ru": "Будет удалён:\n\n%s\n\n"
              "Все данные на нём пропадут безвозвратно.\n"
              "Отменить это действие уже нельзя.",
        "en": "About to delete:\n\n%s\n\n"
              "All data on it will be lost for good.\n"
              "This cannot be undone.",
    },
    "pe_confirm_yes": {"ru": "Да, удалить", "en": "Yes, delete"},
    "pe_cancel": {"ru": "Отмена", "en": "Cancel"},
    "pe_err_title": {"ru": "Не получилось", "en": "Failed"},
    "pe_done_del": {"ru": "Раздел удалён: %s", "en": "Partition deleted: %s"},
    "pe_done_new": {"ru": "Раздел создан: %s", "en": "Partition created: %s"},
    "pe_busy": {"ru": "Работаю, подожди…", "en": "Working, please wait…"},

    "pe_new_title": {"ru": "Создать раздел", "en": "Create partition"},
    "pe_new_avail": {"ru": "Свободно в этом месте: %s", "en": "Free here: %s"},
    "pe_new_size": {"ru": "Размер", "en": "Size"},
    "pe_new_size_ph": {"ru": "например 40G — или оставь пустым, чтобы занять всё",
                       "en": "e.g. 40G — or leave empty to use all of it"},
    "pe_new_fs": {"ru": "Файловая система", "en": "File system"},
    "pe_new_fs_none": {"ru": "Не создавать (пустой раздел)", "en": "None (empty partition)"},
    "pe_new_ok": {"ru": "Создать", "en": "Create"},
    "pe_new_note": {
        "ru": "Точку монтирования назначишь на предыдущем экране.\n"
              "Для раздела EFI выбери fat32 — флаг загрузки поставится сам.",
        "en": "Mount points are assigned on the previous screen.\n"
              "For an EFI partition pick fat32 — the boot flag is set automatically.",
    },
    "pe_bad_size": {"ru": "Не понимаю размер «%s». Примеры: 512M, 40G, 1.5G.",
                    "en": "Cannot read the size “%s”. Examples: 512M, 40G, 1.5G."},
    "pe_size_big": {"ru": "Это больше, чем свободно здесь (%s).",
                    "en": "That is more than the free space here (%s)."},
    "pe_size_small": {"ru": "Слишком мало — нужно хотя бы %s.",
                      "en": "Too small — at least %s is needed."},

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
    "kern_ouvert": {"ru": "linux-ouvert — родное, CachyOS + BORE", "en": "linux-ouvert — native, CachyOS + BORE"},
    "kern_linux": {"ru": "linux — ванильное арчевское", "en": "linux — vanilla Arch"},
    "kern_both": {"ru": "linux-ouvert + lts — запасное в GRUB", "en": "linux-ouvert + lts — GRUB fallback"},
    "kern_lts": {"ru": "linux-lts — долгоживущее, для старого железа", "en": "linux-lts — long-term, for older hardware"},
    "kern_note": {
        "ru": "Не уверен — оставь linux-ouvert. «+ lts» даёт второй пункт\nв меню загрузки: если основное ядро сломается, загрузишься с запасного.",
        "en": "Not sure — keep linux-ouvert. “+ lts” adds a second\nboot menu entry: if the main kernel breaks, boot the fallback.",
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
    # --- этап 5: запреты уровня 1 на странице разметки ---
    "err_root_fs": {
        "ru": "Корень «/» стоит на файловой системе %s — система туда не поставится.\n"
              "Поставь галку «Форматировать» и выбери ext4 или btrfs.",
        "en": "Root “/” sits on a %s filesystem — the system cannot be installed there.\n"
              "Tick “Format” and choose ext4 or btrfs.",
    },
    "err_no_fs": {
        "ru": "На разделе %s нет файловой системы, а он назначен на «%s».\n"
              "Либо поставь галку «Форматировать», либо сними точку монтирования.",
        "en": "Partition %s has no filesystem but is assigned to “%s”.\n"
              "Either tick “Format” or clear the mountpoint.",
    },
    "err_boot_fs": {
        "ru": "«/boot» стоит на файловой системе %s — загрузчик оттуда не запустится.\n"
              "Поставь галку «Форматировать» и выбери ext4.",
        "en": "“/boot” sits on a %s filesystem — the bootloader will not start from it.\n"
              "Tick “Format” and choose ext4.",
    },
    "err_efi_fs": {
        "ru": "«/efi» стоит на файловой системе %s, а EFI-раздел обязан быть FAT32.\n"
              "Возьми настоящий EFI-раздел или отформатируй этот в fat32.",
        "en": "“/efi” sits on a %s filesystem, but an EFI partition must be FAT32.\n"
              "Pick a real EFI partition or format this one as fat32.",
    },
    # --- этап 5: предупреждения уровня 2 (НЕ блокируют «Далее») ---
    "warn_root_small": {
        "ru": "Под корень «/» отведено всего %s. Система с играми туда не влезет — советую от 20 ГиБ.",
        "en": "Only %s is allocated to root “/”. A system with games will not fit — 20 GiB or more is advised.",
    },
    "warn_boot_small": {
        "ru": "«/boot» всего %s. С двумя ядрами место кончится и обновление оборвётся — советую от 512 МиБ.",
        "en": "“/boot” is only %s. With two kernels it will fill up and updates will fail — 512 MiB or more is advised.",
    },
    "warn_esp_full": {
        "ru": "На EFI-разделе %s свободно всего %s, а загрузчику нужно около %s. Установка может оборваться.",
        "en": "EFI partition %s has only %s free, the bootloader needs about %s. Installation may fail.",
    },
    "warn_no_probe": {
        "ru": "Проверить разделы Windows не удалось — защита от их форматирования сейчас не работает.",
        "en": "Could not inspect the Windows partitions — protection against formatting them is inactive.",
    },
    "err_luks_pass": {"ru": "Пароли шифрования не совпадают.", "en": "Encryption passwords do not match."},
    "not_live": {
        "ru": "Установка запускается только с загрузочного ISO.\nКонфиги записаны в /tmp/ouvert для проверки.",
        "en": "Installation only runs from the live ISO.\nConfigs written to /tmp/ouvert for review.",
    },

    "progress_title": {"ru": "Установка", "en": "Installing"},
    "progress_running": {"ru": "Идёт установка. Обычно занимает 10–30 минут — не выключай компьютер.", "en": "Installing. Usually takes 10–30 minutes — do not power off."},
    "progress_done": {"ru": "Готово! Установка завершена.", "en": "Done! Installation complete."},
    "progress_fail": {"ru": "Установка завершилась с ошибкой. Лог ниже и в /tmp/ouvert/install.log", "en": "Installation failed. Log below and in /tmp/ouvert/install.log"},
    "reboot": {"ru": "Перезагрузить", "en": "Reboot"},

    # --- v9: индикатор этапа установки ---
    "stage_prepare": {"ru": "Подготовка…", "en": "Preparing…"},
    "stage_db": {"ru": "Обновление базы пакетов…", "en": "Refreshing package database…"},
    "stage_disk": {"ru": "Разметка диска…", "en": "Partitioning the disk…"},
    "stage_pkgs": {"ru": "Базовая система: %s", "en": "Installing: %s"},
    "stage_profile": {"ru": "Окружение: %s", "en": "Installing desktop: %s"},
    "stage_pkg": {"ru": "Пакеты: %s из %s", "en": "Packages: %s of %s"},
    "stage_fstab": {"ru": "Запись fstab…", "en": "Writing fstab…"},
    "stage_sync": {"ru": "Сброс данных на диск…", "en": "Syncing to disk…"},
}


def tr(key: str) -> str:
    return STRINGS.get(key, {}).get(_LANG, key)


def set_lang(lang: str) -> None:
    global _LANG
    _LANG = lang


def current_lang() -> str:
    return _LANG
