#!/usr/bin/env python3
"""
patch_bug3839.py — PzhavOS, этап 5, сессия 5.

ЧИНИТ ДВА БАГА, НАЙДЕННЫХ КЛИКАМИ НА LOOP-СТЕНДЕ 2 АВГУСТА 2026.

BUG 38 — «512M» превращается в 511 МиБ.
  Начало свободного блока почти никогда не лежит на границе 1 МиБ
  (у первой дыры GPT это 17408 Б). _do_create считал конец раздела
  от СЫРОГО начала: it["start"] + size - 1. Дальше partops.align_range
  двигал начало ВВЕРХ до 1 МиБ, а конец ВНИЗ — и ровно один шаг
  выравнивания у пользователя пропадал.
  Доказано на стенде: ввод 512M → раздел 1 МиБ..511.99 МиБ = 511 МиБ.
  Второй раздел (начало 512 МиБ, уже выровнено) получился ровно 256 МиБ —
  это и подтвердило диагноз.
  ЛЕЧЕНИЕ: считать и «Доступно», и конец от ВЫРОВНЕННОГО начала.

BUG 39 — на MBR-диске fat32 становится неудаляемым «Загрузчиком EFI».
  want_esp = is_fat(fs) без оглядки на таблицу разделов. На msdos флаг
  esp не делает раздел загрузочным для UEFI (msdos так не грузится),
  зато diskmap опознаёт его как EFI и запрещает удаление: пользователь
  запирает сам себя в тупик своим же свежесозданным разделом.
  Доказано на стенде /dev/loop2 (msdos): fat32 → флаг esp → «Удалять
  нельзя: Единственный EFI-раздел на диске».
  ЛЕЧЕНИЕ: автоматический esp только на GPT. Явный esp=True от
  вызывающего по-прежнему уважается — это его осознанный выбор.

СВОЙСТВА ПАТЧА:
  • транзакционный  — все якоря во всех файлах проверяются ДО записи
                      хоть одного байта;
  • идемпотентный   — повторный запуск ничего не делает и говорит об этом;
  • с бэкапом       — *.b3839bak-<метка времени>;
  • компилирует результат в память ДО записи на диск.

ЗАПУСК (из ~/pzhavos/installer):
    python patch_bug3839.py
"""

import py_compile  # noqa: F401  (для явности намерения)
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARTEDIT = HERE / "partedit.py"
PARTOPS = HERE / "partops.py"

STAMP = time.strftime("%Y%m%d-%H%M%S")
SUFFIX = f".b3839bak-{STAMP}"

MARK_EDIT = "def eff_range("
MARK_OPS = "Bug 39"


# ─────────────────────────── тексты замен ───────────────────────────

# --- Bug 38, часть 1: помощник рядом со SLACK ---
A1_OLD = "\ndef parse_size(text):"

A1_NEW = '''
def eff_range(item):
    """Bug 38. Начало свободного блока почти никогда не лежит на границе
    1 МиБ: у первой дыры GPT это 17408 Б. partops.align_range двигает
    начало ВВЕРХ, а конец ВНИЗ, поэтому конец, посчитанный от СЫРОГО
    начала, съедает ровно один шаг выравнивания — «512M» превращалось
    в 511 МиБ.

    Возвращает (выровненное начало, сколько байт от него реально можно
    взять). Оба числа согласованы с тем, что сделает partops.create.
    """
    s, e = partops.align_range(int(item["start"]), int(item["end"]))
    return s, max(0, e - s + 1)


def parse_size(text):'''

# --- Bug 38, часть 2: диалог считает доступное от выровненного начала ---
A2_OLD = '        self.avail = int(free_item["size"])'
A2_NEW = ('        # Bug 38: и «Доступно», и будущий конец — от ВЫРОВНЕННОГО начала.\n'
          '        self.start, self.avail = eff_range(free_item)')

# --- Bug 38, часть 3: запись идёт от того же начала, что показал диалог ---
A3_OLD = ('            path = partops.create(self.disk, it["start"],\n'
          '                                  it["start"] + size - 1, fs)')
A3_NEW = ('            # Bug 38: dlg.start — единственный источник правды о начале.\n'
          '            path = partops.create(self.disk, dlg.start,\n'
          '                                  dlg.start + size - 1, fs)')

# --- Bug 39: esp автоматически только на GPT ---
A4_OLD = "    want_esp = diskmap.is_fat(fs_key) if esp is None else bool(esp)"
A4_NEW = ('    # Bug 39: на msdos флаг esp не делает раздел загрузочным для UEFI\n'
          '    # (msdos так и не грузится), зато diskmap опознаёт его как\n'
          '    # «Загрузчик EFI» и запрещает удаление — пользователь запирает\n'
          '    # сам себя. Автоматически ставим esp ТОЛЬКО на GPT.\n'
          '    # Явный esp=True от вызывающего уважаем как осознанный выбор.\n'
          '    _table = (before["disk"].get("table") or "").lower()\n'
          '    if esp is None:\n'
          '        want_esp = diskmap.is_fat(fs_key) and _table not in ("msdos", "mbr")\n'
          '    else:\n'
          '        want_esp = bool(esp)')

PLAN = [
    (PARTEDIT, [(A1_OLD, A1_NEW), (A2_OLD, A2_NEW), (A3_OLD, A3_NEW)]),
    (PARTOPS, [(A4_OLD, A4_NEW)]),
]


def die(msg):
    print(f"ОТКАЗ: {msg}")
    sys.exit(1)


def main():
    # ── 0. файлы на месте? ──
    for path, _ in PLAN:
        if not path.is_file():
            die(f"не найден {path}. Запускать из ~/pzhavos/installer.")

    src = {path: path.read_text(encoding="utf-8") for path, _ in PLAN}

    # ── 1. идемпотентность ──
    done_edit = MARK_EDIT in src[PARTEDIT]
    done_ops = MARK_OPS in src[PARTOPS]
    if done_edit and done_ops:
        print("Патч уже применён (маркеры на месте). Ничего не делаю.")
        return
    if done_edit != done_ops:
        die("применена ПОЛОВИНА патча: "
            f"partedit={'да' if done_edit else 'нет'}, "
            f"partops={'да' if done_ops else 'нет'}. "
            "Разбирайся руками, автоматом не трогаю.")

    # ── 2. ТРАНЗАКЦИОННОСТЬ: проверяем ВСЕ якоря ДО любой записи ──
    for path, pairs in PLAN:
        for old, _new in pairs:
            n = src[path].count(old)
            if n != 1:
                head = old.strip().splitlines()[0][:60]
                die(f"в {path.name} якорь «{head}…» встречается {n} раз, "
                    "ожидался ровно 1. Файл не тот, что я читал.")
    print("Все 4 якоря найдены по одному разу.")

    # ── 3. собираем результат в памяти ──
    out = {}
    for path, pairs in PLAN:
        text = src[path]
        for old, new in pairs:
            text = text.replace(old, new, 1)
        out[path] = text

    # ── 4. компилируем ДО записи ──
    for path, text in out.items():
        try:
            compile(text, str(path), "exec")
        except SyntaxError as e:
            die(f"результат для {path.name} не компилируется: {e}. "
                "Ничего не записано.")
    print("Оба результата компилируются.")

    # ── 5. бэкап и запись ──
    for path, text in out.items():
        backup = path.with_name(path.name + SUFFIX)
        shutil.copy2(path, backup)
        path.write_text(text, encoding="utf-8")
        was = len(src[path].encode("utf-8"))
        now = len(text.encode("utf-8"))
        print(f"{path.name}: {was} → {now} байт (бэкап: {backup.name})")

    print("\nГОТОВО. Bug 38 и Bug 39 закрыты в коде.")
    print("Проверять — кликами на стендах /dev/loop0 (GPT) и /dev/loop2 (MBR).")


if __name__ == "__main__":
    main()
