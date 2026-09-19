#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_bug4546.py — этап 5, сессия 6.
ЗАКРЫВАЕТ:
  Bug 46 (ВЫСОКИЙ) — метка "loop" принималась за настоящую таблицу.
      parted помечает так диск, на котором ФАЙЛОВАЯ СИСТЕМА ЗАПИСАНА
      ПРЯМО НА УСТРОЙСТВО, без разметки (обычное дело для флешек и
      внешних дисков). Таблицы разделов там нет, но parted печатает
      ОДИН псевдо-раздел №1 во весь диск:
          /dev/loop0:4294967296B:loopback:512:512:loop:Loopback device:;
          1:0B:4294967295B:4294967296B:ext4::;
      Патч 42 ловил только table == "unknown", поэтому редактор считал,
      что таблица есть: рисовал раздел «Начало 0 Б, 4.0 ГиБ, ext4»,
      писал «Этот раздел удалить можно» (удалять нечего, /dev/loop0p1
      не существует) и ГАСИЛ кнопку «Создать таблицу разделов» —
      единственный выход из этого состояния. Тупик класса Bug 34/42.
      ЛЕЧЕНИЕ: "loop" приравнен к "нет таблицы" в ОБОИХ слоях —
      в partedit.reload() и в гейте partops.mklabel().
  Bug 45 (ВЫСОКИЙ) — модалка mklabel утверждала «Диск сейчас пуст,
      терять на нём нечего — данные не пострадают». На loop-диске это
      прямая ложь: там живая ФС, и mklabel её уничтожает. Плюс кнопкой
      по умолчанию стояла «Создать», тогда как в модалке УДАЛЕНИЯ
      с сессии 4 по умолчанию стоит «Отмена» (partedit.py:463).
      Более разрушительная операция была защищена слабее.
      ЛЕЧЕНИЕ: тексты по ветке (unknown → терять нечего; loop →
      предупреждение о потере данных с указанием ФС) и
      setDefaultButton(Отмена).

ПОЧЕМУ КНОПКА НА loop-ДИСКЕ НЕ ЗАПРЕЩЕНА, А РАЗРЕШЕНА С ПРЕДУПРЕЖДЕНИЕМ:
  запрет вернул бы тупик — человеку с флешкой без разметки некуда идти
  средствами live-образа (правило 13.11). Честный текст + «Отмена»
  по умолчанию даёт и защиту, и путь вперёд.

СВОЙСТВА: транзакционный (ВСЕ якоря во ВСЕХ файлах проверяются ДО
первой записи), идемпотентный (маркер, повторный запуск молчит),
защита от «применена половина», бэкапы, compile() перед записью,
размеры считаются В БАЙТАХ (правило 13.18).

ПРАВИТ ТОЛЬКО ~/pzhavos/installer/. Профиль ISO синхронизирует build.sh.
Каталог можно переопределить: PZHAV_INSTALLER=/путь python patch_bug4546.py
"""
import os
import py_compile
import shutil
import sys
import tempfile
import time

BASE = os.environ.get("PZHAV_INSTALLER",
                      os.path.expanduser("~/pzhavos/installer"))
STAMP = time.strftime("%Y%m%d-%H%M%S")

F_I18N = os.path.join(BASE, "i18n.py")
F_OPS = os.path.join(BASE, "partops.py")
F_EDIT = os.path.join(BASE, "partedit.py")

MARKER = "Bug 46"


def read(path):
    if not os.path.isfile(path):
        sys.exit(f"НЕТ ФАЙЛА: {path}")
    with open(path, encoding="utf-8") as f:
        return f.read()


def need(text, anchor, path, n=1):
    got = text.count(anchor)
    if got != n:
        sys.exit(f"ЯКОРЬ НЕ СОШЁЛСЯ в {os.path.basename(path)}: "
                 f"ожидалось {n}, найдено {got}\n  {anchor[:90]!r}")


def sub1(text, old, new, path):
    need(text, old, path, 1)
    return text.replace(old, new, 1)


def nbytes(text):
    """Правило 13.18: размер ТОЛЬКО в байтах. len() на кириллице врёт."""
    return len(text.encode("utf-8"))


# ═══════════════════════ 0. ПРЕДУСЛОВИЯ И ИДЕМПОТЕНТНОСТЬ ═══════════════════

src_i18n = read(F_I18N)
src_ops = read(F_OPS)
src_edit = read(F_EDIT)

done = [MARKER in src_i18n, MARKER in src_ops, MARKER in src_edit]
if all(done):
    print("Патч уже применён (маркер «Bug 46» есть во всех трёх файлах).")
    print("Ничего не делаю.")
    sys.exit(0)
if any(done):
    where = [n for n, d in zip(("i18n.py", "partops.py", "partedit.py"), done) if d]
    sys.exit("ПАТЧ ПРИМЕНЁН НАПОЛОВИНУ — маркер есть только в: "
             + ", ".join(where) + "\nВосстанови файлы из бэкапов и повтори.")

# Предусловие: патч 42 обязан быть на месте, мы правим именно его код.
if "pe_mklabel_text" not in src_i18n:
    sys.exit("НЕ ХВАТАЕТ ПАТЧА 42: в i18n.py нет ключа pe_mklabel_text.")
if "def mklabel" not in src_ops:
    sys.exit("НЕ ХВАТАЕТ ПАТЧА 42: в partops.py нет функции mklabel.")


# ═══════════════════════════ 1. i18n.py ═════════════════════════════════════

A_I18N = '    "pe_mklabel_yes": {"ru": "Создать", "en": "Create"},\n'

NEW_I18N = A_I18N + '''
    # --- сессия 6: Bug 45 и Bug 46, метка "loop": ФС прямо на устройстве ---
    "pe_nolabel_fs": {
        "ru": "На диске %s нет таблицы разделов, но есть файловая система "
              "%s — она занимает весь диск целиком.\\n"
              "Чтобы поставить сюда систему, нужна таблица разделов, "
              "и все данные с диска при этом пропадут.",
        "en": "Disk %s has no partition table, but it does hold a %s "
              "filesystem spanning the whole device.\\n"
              "Installing here needs a partition table, and creating one "
              "will destroy everything on the disk.",
    },
    "pe_hint_nolabel_fs": {
        "ru": "На этом диске нет таблицы разделов: файловая система "
              "записана прямо на устройство.\\n"
              "Так бывает у флешек и внешних дисков. Разделов тут нет "
              "и не будет, пока не создана таблица.",
        "en": "This disk has no partition table: the filesystem is written "
              "straight onto the device.\\n"
              "Common for flash drives and external disks. It has no "
              "partitions and cannot have any until a table is created.",
    },
    "pe_mklabel_text_fs": {
        "ru": "На диске %s будет создана таблица разделов %s.\\n\\n"
              "ВНИМАНИЕ: сейчас на диске лежит файловая система %s, "
              "записанная прямо на устройство. Все данные на ней "
              "пропадут безвозвратно.\\n\\n"
              "Если там есть что-то нужное — нажми «Отмена» и сначала "
              "скопируй файлы в другое место.",
        "en": "A partition table will be created on %s: %s.\\n\\n"
              "WARNING: the disk currently holds a %s filesystem written "
              "straight onto the device. All data on it will be lost "
              "for good.\\n\\n"
              "If anything there matters, press \\u201cCancel\\u201d and copy "
              "the files elsewhere first.",
    },
'''

out_i18n = sub1(src_i18n, A_I18N, NEW_I18N, F_I18N)


# ═══════════════════════════ 2. partops.py ══════════════════════════════════

A_OPS_DOC = """    Сознательно НЕ умеет перезаписывать существующую таблицу: mklabel
"""

NEW_OPS_DOC = """    ★ Bug 46: метка "loop" — это НЕ таблица разделов, а признак того, что
    файловая система записана прямо на устройство. Считать её живой
    таблицей нельзя: тогда разметить такой диск станет нечем. Создавать
    таблицу здесь МОЖНО, но данные на этой ФС гибнут — предупреждение
    обязательно на стороне GUI (Bug 45).

    Сознательно НЕ умеет перезаписывать существующую таблицу: mklabel
"""

A_OPS_CUR = """    cur = (m.get("disk") or {}).get("table", "")
    if cur and cur != "unknown":
"""

NEW_OPS_CUR = """    cur = (m.get("disk") or {}).get("table", "")
    # Bug 46: "loop" приравнен к отсутствию таблицы — см. docstring.
    if cur and cur not in ("unknown", "loop"):
"""

out_ops = sub1(src_ops, A_OPS_DOC, NEW_OPS_DOC, F_OPS)
out_ops = sub1(out_ops, A_OPS_CUR, NEW_OPS_CUR, F_OPS)


# ═══════════════════════════ 3. partedit.py ═════════════════════════════════

A_ED_INIT = """        self.can_write, self.why_ro = partops.write_allowed(self.disk)
        m, ctx, sample = read_all(self.disk)
"""

NEW_ED_INIT = """        self.can_write, self.why_ro = partops.write_allowed(self.disk)
        # Bug 46: непустая строка = на диске ФС прямо на устройстве, без
        # таблицы разделов. Сбрасываем на КАЖДОМ reload, до всех ветвлений:
        # значение читает _do_mklabel, и протухшее здесь опаснее пустого.
        self.fs_whole = ""
        m, ctx, sample = read_all(self.disk)
"""

A_ED_RELOAD = """        if (m.get("disk") or {}).get("table", "") in ("unknown", ""):
            self.items = []
            self.table.setRowCount(0)
            self.hint.setText(tr("pe_hint_nolabel"))
            self.btn_del.setEnabled(False)
            self.btn_new.setEnabled(False)
            self.btn_label.setEnabled(self.can_write)
            self.btn_label.setToolTip("" if self.can_write else self.why_ro)
            self._say(tr("pe_nolabel") % self.disk, CORAL)
            return
"""

NEW_ED_RELOAD = """        # Bug 46: "loop" — ШЕСТОЙ тип метки, и он тоже означает «таблицы
        # разделов нет». Так parted помечает диск, на котором ФС записана
        # прямо на устройство. Псевдо-раздел №1 во весь диск, который он
        # при этом печатает, — НЕ раздел: узла /dev/...p1 не существует,
        # удалять там нечего. До этой правки он попадал в таблицу и гасил
        # кнопку создания метки, то есть запирал пользователя.
        # ★ ОТЛИЧИЕ ОТ "unknown": здесь на диске ЖИВЫЕ ДАННЫЕ, поэтому
        #   тексты предупреждений другие (Bug 45).
        _table = (m.get("disk") or {}).get("table", "")
        if _table == "loop":
            self.fs_whole = next(
                (i.get("fstype") for i in m.get("items", [])
                 if i["kind"] == "part" and i.get("fstype")), "") or "?"
        if _table in ("unknown", "loop", ""):
            self.items = []
            self.table.setRowCount(0)
            self.hint.setText(tr("pe_hint_nolabel_fs") if self.fs_whole
                              else tr("pe_hint_nolabel"))
            self.btn_del.setEnabled(False)
            self.btn_new.setEnabled(False)
            self.btn_label.setEnabled(self.can_write)
            self.btn_label.setToolTip("" if self.can_write else self.why_ro)
            if self.fs_whole:
                self._say(tr("pe_nolabel_fs") % (self.disk, self.fs_whole),
                          CORAL)
            else:
                self._say(tr("pe_nolabel") % self.disk, CORAL)
            return
"""

A_ED_BOX = """        box.setText(tr("pe_mklabel_text") % (self.disk, shown))
        yes = box.addButton(tr("pe_mklabel_yes"),
                            QMessageBox.ButtonRole.AcceptRole)
        box.addButton(tr("pe_cancel"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
"""

NEW_ED_BOX = """        # Bug 45: на loop-диске обещать «данные не пострадают» — ложь.
        if self.fs_whole:
            box.setText(tr("pe_mklabel_text_fs")
                        % (self.disk, shown, self.fs_whole))
        else:
            box.setText(tr("pe_mklabel_text") % (self.disk, shown))
        yes = box.addButton(tr("pe_mklabel_yes"),
                            QMessageBox.ButtonRole.AcceptRole)
        no = box.addButton(tr("pe_cancel"), QMessageBox.ButtonRole.RejectRole)
        # Bug 45: по умолчанию — НЕ создавать. Операция разрушительнее
        # удаления раздела, а там setDefaultButton стоит с сессии 4.
        box.setDefaultButton(no)
        box.exec()
"""

out_edit = sub1(src_edit, A_ED_INIT, NEW_ED_INIT, F_EDIT)
out_edit = sub1(out_edit, A_ED_RELOAD, NEW_ED_RELOAD, F_EDIT)
out_edit = sub1(out_edit, A_ED_BOX, NEW_ED_BOX, F_EDIT)


# ═══════════════ 4. КОМПИЛЯЦИЯ ДО ЕДИНОЙ ЗАПИСИ НА ДИСК ═════════════════════

def check_compiles(text, name):
    tmp = os.path.join(tempfile.gettempdir(), f"pzhav-{name}")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        py_compile.compile(tmp, cfile=tmp + "c", doraise=True)
    except py_compile.PyCompileError as exc:
        sys.exit(f"НОВЫЙ {name} НЕ КОМПИЛИРУЕТСЯ, НИЧЕГО НЕ ЗАПИСАНО:\n{exc}")
    finally:
        for p in (tmp, tmp + "c"):
            try:
                os.remove(p)
            except OSError:
                pass


check_compiles(out_i18n, "i18n.py")
check_compiles(out_ops, "partops.py")
check_compiles(out_edit, "partedit.py")


# ═══════════════════════ 5. БЭКАПЫ И ЗАПИСЬ ═════════════════════════════════

plan = [(F_I18N, src_i18n, out_i18n),
        (F_OPS, src_ops, out_ops),
        (F_EDIT, src_edit, out_edit)]

for path, old, new in plan:
    bak = f"{path}.b4546bak-{STAMP}"
    shutil.copy2(path, bak)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"{os.path.basename(path):14s} {nbytes(old):6d} → {nbytes(new):6d} Б"
          f"   бэкап: {os.path.basename(bak)}")

print()
print("ГОТОВО. Проверь на хосте:")
print('  grep -c "loop" ~/pzhavos/installer/partops.py')
print('  wc -c ~/pzhavos/installer/partedit.py ~/pzhavos/installer/partops.py')
