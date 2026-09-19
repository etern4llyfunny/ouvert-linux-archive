#!/usr/bin/env python3
"""ПАТЧ 51 — Alt+Shift в COSMIC.

ЧТО ДЕЛАЕТ: добавляет в build_custom_commands() шестой слой раскладки —
            ~/.config/cosmic/com.system76.CosmicComp/v1/xkb_config для
            всех /home/*. Три поля; model/repeat_* COSMIC допишет сам.

ОСНОВАНИЕ:  замер 9.8 на t27 10.08.26 — частичная RON-структура ПРИНЯТА,
            доказано немецким маркером (qwertzuiop) после перелогина.

ФАЙЛОВ:     один — config_gen.py. Ни PKGBUILD, ни пакета, ни репо.

ИДЕМПОТЕНТЕН: повторный запуск отказывается работать, не портя файл.

Запуск:  python3 patch_cosmic51.py [путь-к-config_gen.py]
"""
import py_compile
import shutil
import sys
import time
from pathlib import Path

SIZE_BEFORE = 38594
MARKER = "Bug 51 cosmic"

# Якорь разбит НАДВОЕ намеренно: вставка идёт МЕЖДУ последней строкой
# литерала и закрывающей скобкой cmds.append(). Вставить перед HEAD =
# порвать f-string на строке 222 (поймано контрольным прогоном 10.08.26).
HEAD = ' >> /etc/environment\\n"\n'
TAIL = '        )\n'
ANCHOR = HEAD + TAIL

INSERT = '''            # \u2605 Bug 51 cosmic: COSMIC игнорирует И xorg.conf.d, И
            # /etc/environment — cosmic-comp пишет СВОЙ xkb_config, наши
            # переменные до него не доезжают (диагноз 9.5, t27 09.08.26).
            # Кладём ТРИ поля: model/repeat_delay/repeat_rate COSMIC
            # допишет сам — ЗАМЕР 9.8 на t27 10.08.26, частичная
            # RON-структура ПРИНЯТА (маркер de -> qwertzuiop). Навязывать
            # юзеру модель клавиатуры и автоповтор — не наше дело.
            # Гейта [ -d /usr/share/cosmic ] тут НЕТ намеренно: файл в
            # ~/.config без COSMIC безвреден, а юзер мог доставить COSMIC
            # вторым столом. Юзер создаётся ДО этих команд -> /etc/skel
            # уже не доедет, разносим по /home/* сами (логика kxkbrc).
            # \u26a0 ДЫРА: юзер, созданный ПОСЛЕ установки, файла не получит.
            #   Системного аналога /etc/xdg у cosmic-config не искали.
            "for h in /home/*; do\\n"
            "  [ -d \\"$h\\" ] || continue\\n"
            "  u=$(basename \\"$h\\")\\n"
            "  d=\\"$h/.config/cosmic/com.system76.CosmicComp/v1\\"\\n"
            "  if [ ! -e \\"$d/xkb_config\\" ]; then\\n"
            "    mkdir -p \\"$d\\"\\n"
            "    cat > \\"$d/xkb_config\\" <<'CXKBEOF'\\n"
            "(\\n"
            f"    layout: \\"{layout}\\",\\n"
            f"    variant: \\"{',' * layout.count(',')}\\",\\n"
            f"    options: Some(\\"{opts}\\"),\\n"
            ")\\n"
            "CXKBEOF\\n"
            "    chown -R \\"$u:$u\\" \\"$h/.config\\" 2>/dev/null || true\\n"
            "  fi\\n"
            "done\\n"
'''


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
        die(f"размер {size}, ожидался {SIZE_BEFORE} — это не тот файл")

    n_mark = src.count(MARKER)
    if n_mark:
        die(f"маркер «{MARKER}» уже есть ({n_mark}) — патч применён ранее")

    n_anchor = src.count(ANCHOR)
    if n_anchor != 1:
        die(f"якорь найден {n_anchor} раз, нужен ровно 1")
    print("\u2022 якорь:  1 \u2713   маркер: 0 \u2713")

    # --- бэкап ---
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = path.with_suffix(path.suffix + f".b51bak-{stamp}")
    shutil.copy2(path, bak)
    if bak.stat().st_size != size:
        die("бэкап не совпал по размеру")
    print(f"\u2022 бэкап:  {bak.name} ({bak.stat().st_size} Б) \u2713")

    # --- запись ---
    new = src.replace(ANCHOR, HEAD + INSERT + TAIL, 1)
    delta = len(new.encode("utf-8")) - size
    path.write_text(new, encoding="utf-8")

    got = path.stat().st_size
    print(f"\u2022 стало:  {got} Б  (+{delta})")
    if got != size + delta:
        die("размер после записи не сошёлся — ОТКАТИ ИЗ БЭКАПА")

    # --- синтаксис ---
    try:
        py_compile.compile(str(path), doraise=True, cfile="/tmp/_p51.pyc")
    except py_compile.PyCompileError as e:
        shutil.copy2(bak, path)
        die(f"синтаксис сломан, ОТКАЧЕНО из бэкапа:\n{e}")
    print("\u2022 python -m py_compile \u2713")

    # --- перепроверка маркера ---
    if path.read_text(encoding="utf-8").count(MARKER) != 1:
        die("маркер после записи не равен 1 — ОТКАТИ ИЗ БЭКАПА")

    print(f"\n\u2714 ПАТЧ 51 ПРИМЕНЁН.  {size} \u2192 {got} Б")
    print("  Дальше: python3 t_cosmic51.py  (обязан пройти 16/16)")


if __name__ == "__main__":
    main()
