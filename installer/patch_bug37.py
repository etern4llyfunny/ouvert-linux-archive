#!/usr/bin/env python3
"""
patch_bug37.py — BUG 37 (найден живьём на loop-стенде, сессия 4).

СИМПТОМ: окно пишет «Свободно в этом месте: 3.5 ГиБ», пользователь вводит
3.5G и получает отказ «Это больше, чем свободно здесь (3.5 ГиБ)».
Показанное число невозможно ввести обратно — интерфейс спорит сам с собой.

ПРИЧИНА: свободно 3 758 079 488 Б, а 3.5G = 3 758 096 384 Б. Разница
16 КиБ, но human() округляет ВВЕРХ до «3.5 ГиБ». Ловушка округления:
показываем округлённое, а сравниваем точное.

ЧАСТЬ Б: «3.5ГиБ» кириллицей не разбиралось, хотя интерфейс сам пишет
«ГиБ» русскими буквами. Человек копирует то, что видит.

ЧТО ДЕЛАЕМ:
  1. parse_size понимает кириллические К/М/Г/Т и суффиксы Б/иБ.
  2. Допуск SLACK = 1 МиБ: запрошено чуть больше доступного → молча
     берём весь блок. Резать до байта бессмысленно — partops всё равно
     выравнивает конец ВНИЗ до границы 1 МиБ.
     Больше допуска — отказ остаётся, и это правильно: «10G» вместо
     «3.5 ГиБ» это не округление, а промах пользователя.
  3. Статус для свободной строки: «Здесь можно создать раздел» вместо
     «покажу, можно ли её удалить» — для пустого места это бессмыслица.

ПРИНЦИПЫ: транзакционный, идемпотентный, py_compile до записи,
бэкапы .b37bak-*. Профиль не трогается — см. patch_session4.py.
"""

import datetime
import os
import py_compile
import sys
import tempfile

MARK = "SLACK"
ROOTS = [os.path.expanduser("~/pzhavos/installer")]
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


# ── partedit.py ──────────────────────────────────────────────────────

PE1_OLD = '''_UNITS = {"k": 1024, "m": 1024 ** 2, "g": 1024 ** 3, "t": 1024 ** 4}


def parse_size(text):
    """«40G», «512M», «1,5G», «2048» (МиБ) → байты. None — не разобрал.

    Голое число трактуется как МиБ: человек, пишущий «512», имеет в виду
    мегабайты, а не полкилобайта. Байтов от руки никто не вводит.
    """
    s = (text or "").strip().lower().replace(",", ".").replace(" ", "")
    if not s:
        return None
    if s.endswith("ib"):
        s = s[:-2]
    elif s.endswith("b"):
        s = s[:-1]
    mult = 1024 ** 2
    if s and s[-1] in _UNITS:
        mult = _UNITS[s[-1]]
        s = s[:-1]
'''

PE1_NEW = '''_UNITS = {"k": 1024, "m": 1024 ** 2, "g": 1024 ** 3, "t": 1024 ** 4}

# Bug 37б: интерфейс пишет «3.5 ГиБ» кириллицей, человек копирует то, что
# видит. Отказать ему за это — издевательство.
_CYR = {"к": "k", "м": "m", "г": "g", "т": "t", "б": "b", "и": "i"}

# Bug 37а: human() округляет ВВЕРХ, поэтому показанный размер бывает
# на несколько КиБ больше настоящего. Допуск в 1 МиБ закрывает щель.
# Риска нет: partops.align_range всё равно режет конец ВНИЗ до границы.
SLACK = 1024 * 1024


def parse_size(text):
    """«40G», «512M», «1,5G», «3.5 ГиБ», «2048» (МиБ) → байты.
    None — не разобрал.

    Голое число трактуется как МиБ: человек, пишущий «512», имеет в виду
    мегабайты, а не полкилобайта. Байтов от руки никто не вводит.
    """
    s = (text or "").strip().lower().replace(",", ".").replace(" ", "")
    s = "".join(_CYR.get(ch, ch) for ch in s)
    if not s:
        return None
    if s.endswith("ib"):
        s = s[:-2]
    elif s.endswith("b"):
        s = s[:-1]
    mult = 1024 ** 2
    if s and s[-1] in _UNITS:
        mult = _UNITS[s[-1]]
        s = s[:-1]
'''

PE2_OLD = '''            if size > self.avail:
                self.err.setText(tr("pe_size_big")
                                 % diskmap.human(self.avail))
                return
'''

PE2_NEW = '''            if size > self.avail + SLACK:
                self.err.setText(tr("pe_size_big")
                                 % diskmap.human(self.avail))
                return
            # Промах на пару КиБ из-за округления показанного числа —
            # это не «мало места», это наша же цифра вернулась обратно.
            size = min(size, self.avail)
'''

PE3_OLD = '''        if it["kind"] == "free":
            self._say(tr("pe_select"), MUTED)
            return
'''

PE3_NEW = '''        if it["kind"] == "free":
            self._say(tr("pe_can_create"), MUTED)
            return
'''

# ── i18n.py ──────────────────────────────────────────────────────────

I1_OLD = '''    "pe_pick_free": {"ru": "Сначала выбери свободное место (бирюзовая строка).",
                     "en": "Select free space first (the teal row)."},
'''

I1_NEW = '''    "pe_pick_free": {"ru": "Сначала выбери свободное место (бирюзовая строка).",
                     "en": "Select free space first (the teal row)."},
    "pe_can_create": {"ru": "Здесь можно создать раздел.",
                      "en": "You can create a partition here."},
'''

PLAN = [
    ("partedit.py", [(PE1_OLD, PE1_NEW), (PE2_OLD, PE2_NEW),
                     (PE3_OLD, PE3_NEW)]),
    ("i18n.py", [(I1_OLD, I1_NEW)]),
]


def main():
    print(f"patch_bug37  {STAMP}")
    staged = {}
    for root in ROOTS:
        print(f"\n[{root}]")
        if not os.path.isdir(root):
            print("    ПРОПУСК: каталога нет")
            continue
        for fname, pairs in PLAN:
            path = os.path.join(root, fname)
            if not os.path.exists(path):
                print(f"    ПРОПУСК: нет {fname}")
                continue
            src = open(path, encoding="utf-8").read()
            mark = MARK if fname == "partedit.py" else "pe_can_create"
            if mark in src:
                print(f"    уже применён: {fname}")
                continue
            for old, new in pairs:
                n = src.count(old)
                assert n == 1, (f"{path}: якорь встречается {n} раз, "
                                f"ожидался 1.\n--- ЯКОРЬ ---\n{old[:200]}")
                src = src.replace(old, new, 1)
            staged[path] = src
            print(f"    готов: {fname} ({len(src.encode('utf-8'))} байт)")

    if not staged:
        print("\nНечего делать.")
        return 0

    for path, text in staged.items():
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                         encoding="utf-8") as t:
            t.write(text)
            tmp = t.name
        try:
            py_compile.compile(tmp, doraise=True, cfile=tmp + "c")
        except py_compile.PyCompileError as e:
            print(f"\nОТМЕНА: {os.path.basename(path)} не компилируется:\n{e}")
            return 1
        finally:
            os.unlink(tmp)
    print("\npy_compile: валидны")

    for path, text in staged.items():
        bak = f"{path}.b37bak-{STAMP}"
        with open(bak, "w", encoding="utf-8") as f:
            f.write(open(path, encoding="utf-8").read())
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"записан {path}")

    print("\nГОТОВО.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
