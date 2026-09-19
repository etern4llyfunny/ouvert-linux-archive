"""ПАТЧ 55: раскладка через /etc/vconsole.conf (localed) вместо localectl.

Что делает:
  1. УДАЛЯЕТ блок патча 54 (вызов `localectl set-x11-keymap` в чруте).
  2. ВСТАВЛЯЕТ вместо него два блока:
       а) запись XKB* + KEYMAP в /etc/vconsole.conf  — источник правды localed
       б) запись /etc/X11/xorg.conf.d/00-keyboard.conf — для X11-сессий
  3. Слои kxkbrc / dconf / /etc/environment НЕ ТРОГАЕТ.

Транзакционность: бэкап -> запись -> py_compile; при любой ошибке файл
возвращается из бэкапа, на диске остаётся исходник.

Запуск:  python patch_vconsole55.py [путь_к_config_gen.py]
"""
import datetime
import py_compile
import shutil
import sys
from pathlib import Path

TARGET = Path(sys.argv[1] if len(sys.argv) > 1 else "config_gen.py")

# --- якоря. HEAD/TAIL, а не «вставить перед строкой»: патч 51 порвал
# --- f-string ровно потому, что резал по середине литерала (13-в).
HEAD = "        # ★ Bug 54 localed:"
TAIL = "\n\n        # --- PzhavOS: раскладка для DE"

NEW = '''        # ★ Bug 55 vconsole: НИЖНИЙ СЛОЙ РАСКЛАДКИ — localed, но говорить
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
            "touch /etc/vconsole.conf\\n"
            "sed -i '/^KEYMAP=/d;/^XKBLAYOUT=/d;/^XKBMODEL=/d;"
            "/^XKBVARIANT=/d;/^XKBOPTIONS=/d' /etc/vconsole.conf || true\\n"
            "cat >> /etc/vconsole.conf <<'VCEOF'\\n"
            f"KEYMAP={kb['kb_layout']}\\n"
            f"XKBLAYOUT={layout}\\n"
            "XKBMODEL=pc105+inet\\n"
            f"XKBVARIANT={variant}\\n"
            f"XKBOPTIONS={opts}\\n"
            "VCEOF\\n"
        )

        # Слой Xorg. COSMIC и KDE-Wayland берут раскладку из localed по
        # D-Bus, а X11-сессии (XFCE+LightDM — наш дефолт) читают
        # именно этот файл. Формально он принадлежит localed (13.40),
        # но гонки нет: localed генерирует его ИЗ vconsole.conf, который
        # мы только что заполнили — перезапись даст тот же текст.
        # Формат снят с живого файла на t27, не выдуман.
        cmds.append(
            "mkdir -p /etc/X11/xorg.conf.d\\n"
            "cat > /etc/X11/xorg.conf.d/00-keyboard.conf <<'XORGEOF'\\n"
            'Section "InputClass"\\n'
            '        Identifier "system-keyboard"\\n'
            '        MatchIsKeyboard "on"\\n'
            f'        Option "XkbLayout" "{layout}"\\n'
            '        Option "XkbModel" "pc105+inet"\\n'
            f'        Option "XkbVariant" "{variant}"\\n'
            f'        Option "XkbOptions" "{opts}"\\n'
            "EndSection\\n"
            "XORGEOF\\n"
        )'''


def die(msg):
    print(f"✘ {msg}")
    sys.exit(1)


def main():
    if not TARGET.exists():
        die(f"нет файла {TARGET}")

    src = TARGET.read_text(encoding="utf-8")
    before = len(src.encode("utf-8"))
    print(f"исходный размер: {before} Б")

    # --- идемпотентность
    if "Bug 55 vconsole" in src:
        die("патч уже применён (найден маркер 'Bug 55 vconsole')")

    # --- якоря должны быть уникальны
    if src.count(HEAD) != 1:
        die(f"HEAD встречается {src.count(HEAD)} раз, ожидалось 1")
    if src.count(TAIL) != 1:
        die(f"TAIL встречается {src.count(TAIL)} раз, ожидалось 1")

    i = src.index(HEAD)
    j = src.index(TAIL, i)
    old = src[i:j]

    if "localectl set-x11-keymap" not in old:
        die("в вырезаемом блоке нет localectl — файл не тот, что ожидался")

    bak = TARGET.with_suffix(
        TARGET.suffix + ".b55bak-" +
        datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(TARGET, bak)
    print(f"бэкап: {bak.name}")

    try:
        TARGET.write_text(src[:i] + NEW + src[j:], encoding="utf-8")
        py_compile.compile(str(TARGET), doraise=True)
    except Exception as e:
        shutil.copy2(bak, TARGET)
        die(f"ОТКАТ из бэкапа: {e}")

    after = len(TARGET.read_text(encoding="utf-8").encode("utf-8"))
    print(f"новый размер:    {after} Б  ({after - before:+d})")

    # --- контроль ПО СГЕНЕРИРОВАННОМУ ВЫВОДУ (13.36), а не по исходнику
    sys.path.insert(0, str(TARGET.parent.resolve()))
    for m in ("config_gen", "desktops"):
        sys.modules.pop(m, None)
    try:
        import config_gen  # noqa: E402
        out = "".join(config_gen.build_custom_commands({"kb": "us_ru"}))
    except Exception as e:
        shutil.copy2(bak, TARGET)
        die(f"ОТКАТ: сгенерировать команды не вышло: {e}")

    control = [
        ("localectl set-x11-keymap", 0),
        ("cat >> /etc/vconsole.conf", 1),
        ("XKBLAYOUT=us,ru", 1),
        ("XKBOPTIONS=grp:alt_shift_toggle", 1),
        ("KEYMAP=us", 1),
        ("cat > /etc/X11/xorg.conf.d/00-keyboard.conf", 1),
        ("LayoutList=us,ru", 1),          # старый слой KDE жив
        ("XKB_DEFAULT_LAYOUT=us,ru", 1),  # старый слой environment жив
    ]
    bad = []
    for needle, want in control:
        got = out.count(needle)
        print(f"  {'ok  ' if got == want else 'FAIL'} \"{needle}\": {got}, ожидалось {want}")
        if got != want:
            bad.append(needle)

    if bad:
        shutil.copy2(bak, TARGET)
        die(f"ОТКАТ из бэкапа: контроль не сошёлся: {bad}")

    print("✔ патч 55 применён, контроль 8/8")


if __name__ == "__main__":
    main()
