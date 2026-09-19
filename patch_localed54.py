#!/usr/bin/env python3
"""ПАТЧ 54 — localed как единый нижний слой раскладки.

ОСНОВАНИЕ: замер на t27 10.08.26. COSMIC при первом входе читает
           systemd-localed, а НЕ наш файл. localectl set-x11-keymap
           -> логаут -> Alt+Shift дал «йцукенгшщз». Диагноз 9.3 из v23,
           объявленный ложным, оказался ВЕРНЫМ (негодны были улики).

ТРИ ОПЕРАЦИИ:
  1. УДАЛИТЬ ручную запись /etc/X11/xorg.conf.d/00-keyboard.conf.
     Файл ПРИНАДЛЕЖИТ systemd-localed — он его перезаписывает и
     подставляет свой terminate:ctrl_alt_bksp. Мы писали в чужое.
  2. УДАЛИТЬ COSMIC-блок патча 51 (~/.config/.../xkb_config).
     COSMIC затирает его при первом входе данными из localed.
  3. ВСТАВИТЬ localectl set-x11-keymap вместо (1).

ОСТАЮТСЯ НЕТРОНУТЫМИ: kxkbrc (KDE), dconf (GNOME/Cinnamon),
                      /etc/environment (голые композиторы).

ИДЕМПОТЕНТЕН. Запуск: python3 patch_localed54.py [config_gen.py]
"""
import py_compile
import shutil
import sys
import time
from pathlib import Path

SIZE_BEFORE = 40551
MARKER = "Bug 54 localed"

# --- 1. удаляемый блок: ручная запись 00-keyboard.conf ---
DEL_XORG = '''        cmds.append(
            "set -e\\n"
            "mkdir -p /etc/X11/xorg.conf.d\\n"
            "cat > /etc/X11/xorg.conf.d/00-keyboard.conf <<'XKBEOF'\\n"
            'Section "InputClass"\\n'
            '    Identifier "system-keyboard"\\n'
            '    MatchIsKeyboard "on"\\n'
            f'    Option "XkbLayout" "{layout}"\\n'
            f'    Option "XkbOptions" "{opts}"\\n'
            "EndSection\\n"
            "XKBEOF\\n"
        )
'''

# --- 1'. что встаёт на его место ---
NEW_LOCALED = '''        # \u2605 Bug 54 localed: НИЖНИЙ СЛОЙ РАСКЛАДКИ — ОДИН, И ЭТО localed.
        # Раньше здесь руками писался /etc/X11/xorg.conf.d/00-keyboard.conf.
        # Файл ПРИНАДЛЕЖИТ systemd-localed: тот перезаписывает его целиком
        # и подставляет СВОЙ terminate:ctrl_alt_bksp вместо нашей опции.
        # Замер на t27 10.08.26: COSMIC при ПЕРВОМ ВХОДЕ читает localed по
        # D-Bus и пишет полученное себе в xkb_config. Отсюда «одна раскладка
        # us» после установки — не COSMIC виноват, а затёртый localed'ом файл.
        # localectl пишет И xorg.conf.d, И XKB* в /etc/vconsole.conf, И
        # отдаёт значения по D-Bus. Один вызов вместо файла, спорить не с кем.
        # \u2605 ПРОВЕРЕНО КЛИКАМИ: set-x11-keymap -> логаут -> Alt+Shift ->
        #   «йцукенгшщз». Это ТРЕТИЙ раз, когда запись в чужой файл вышла
        #   боком (шрам KDE `Next`, /usr/share/cosmic, теперь 00-keyboard).
        # || true: localectl требует живой D-Bus. В чруте он есть (systemd
        # смонтирован), но падение не должно валить установку.
        cmds.append(
            f'localectl set-x11-keymap "{layout}" "pc105+inet" '
            f'"{"," * layout.count(",")}" "{opts}" || true\\n'
        )
'''

# --- 2. удаляемый блок: COSMIC xkb_config из патча 51 ---
DEL_COSMIC_HEAD = "            # \u2605 Bug 51 cosmic: COSMIC игнорирует И xorg.conf.d, И\n"
DEL_COSMIC_TAIL = '            "done\\n"\n        )\n'


def die(msg):
    print(f"\u2718 ОТКАЗ: {msg}")
    print("  Файл НЕ ТРОНУТ.")
    sys.exit(1)


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "config_gen.py")
    if not path.is_file():
        die(f"нет файла {path}")

    src = path.read_text(encoding="utf-8")
    size = len(src.encode("utf-8"))
    print(f"\u2022 файл:   {path}")
    print(f"\u2022 байт:   {size}")

    if size != SIZE_BEFORE:
        die(f"размер {size}, ожидался {SIZE_BEFORE} — патч 51 не применён?")
    if src.count(MARKER):
        die(f"маркер «{MARKER}» уже есть — патч применён ранее")

    # якоря
    if src.count(DEL_XORG) != 1:
        die(f"xorg-блок найден {src.count(DEL_XORG)} раз, нужен 1")
    i = src.find(DEL_COSMIC_HEAD)
    if i < 0 or src.count(DEL_COSMIC_HEAD) != 1:
        die("cosmic-блок (голова) не найден или не уникален")
    j = src.find(DEL_COSMIC_TAIL, i)
    if j < 0:
        die("cosmic-блок (хвост) не найден после головы")
    print("\u2022 якоря:  3/3 \u2713   маркер: 0 \u2713")

    # --- бэкап ---
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = path.with_suffix(path.suffix + f".b54bak-{stamp}")
    shutil.copy2(path, bak)
    if bak.stat().st_size != size:
        die("бэкап не совпал по размеру")
    print(f"\u2022 бэкап:  {bak.name} ({bak.stat().st_size} Б) \u2713")

    # --- правка ---
    # 2: вырезаем cosmic-блок (от головы до конца done, хвост ")" оставляем)
    cosmic_block = src[i:j] + '            "done\\n"\n'
    new = src.replace(cosmic_block, "", 1)
    if new.count("CXKBEOF"):
        shutil.copy2(bak, path)
        die("после вырезания cosmic-блока остался CXKBEOF — ОТКАЧЕНО")
    # 1: подменяем xorg-блок на localectl
    if new.count(DEL_XORG) != 1:
        shutil.copy2(bak, path)
        die("xorg-блок исчез после первой правки — ОТКАЧЕНО")
    new = new.replace(DEL_XORG, NEW_LOCALED, 1)

    delta = len(new.encode("utf-8")) - size
    path.write_text(new, encoding="utf-8")
    got = path.stat().st_size
    print(f"\u2022 стало:  {got} Б  ({delta:+d})")

    # --- синтаксис ---
    try:
        py_compile.compile(str(path), doraise=True, cfile="/tmp/_p54.pyc")
    except py_compile.PyCompileError as e:
        shutil.copy2(bak, path)
        die(f"синтаксис сломан, ОТКАЧЕНО:\n{e}")
    print("\u2022 python -m py_compile \u2713")

    chk = path.read_text(encoding="utf-8")
    for name, cnt, want in (
        (MARKER, chk.count(MARKER), 1),
        ("CXKBEOF", chk.count("CXKBEOF"), 0),
        ("cat > /etc/X11", chk.count("cat > /etc/X11"), 0),
        ("mkdir /etc/X11", chk.count("mkdir -p /etc/X11"), 0),
        ("localectl set-x11-keymap", chk.count("localectl set-x11-keymap"), 1),
        ("kxkbrc", chk.count("/etc/skel/.config/kxkbrc"), 3),
    ):
        if cnt != want:
            shutil.copy2(bak, path)
            die(f"контроль «{name}»: {cnt}, ожидалось {want} — ОТКАЧЕНО")
    print("\u2022 контроль содержимого 6/6 \u2713")

    print(f"\n\u2714 ПАТЧ 54 ПРИМЕНЁН.  {size} \u2192 {got} Б")
    print("  Дальше: python3 t_localed54.py  (обязан пройти)")


if __name__ == "__main__":
    main()
