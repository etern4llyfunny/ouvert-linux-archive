#!/usr/bin/env python3
"""
patch_session4.py — ЭТАП 5, СЕССИЯ 4: ИНТЕГРАЦИЯ partops В ДИАЛОГ.

ЧТО ДЕЛАЕТ:
  i18n.py     — новые строки редактора (создание/подтверждение/ошибки),
                правка pe_hint (там висело враньё «изменение появится позже»)
  partedit.py — кнопки «Удалить»/«Создать» оживают, уровень 3
                (подтверждение), диалог создания раздела

ПРИНЦИПЫ (правила проекта):
  • ТРАНЗАКЦИОННЫЙ: все якоря всех файлов проверяются ДО первой записи.
    Не сошёлся хоть один — не пишется НИЧЕГО.
  • ИДЕМПОТЕНТНЫЙ: повторный запуск говорит «уже применён» и выходит.
  • ОБЕ КОПИИ: installer/ и iso/profile/airootfs/opt/pzhavos-installer/.
    Копии, которых нет, ПРОПУСКАЮТСЯ с явным сообщением (в профиле
    сейчас partedit.py нет вообще — см. очередь v19, пункт 7).
  • БЭКАПЫ: file.s4bak-YYYYmmdd-HHMMSS рядом с оригиналом.
"""

import datetime
import os
import py_compile
import sys
import tempfile

MARK = "pe_new_title"          # маркер применённости (ключ i18n)
MARK_PE = "def _do_delete"     # маркер применённости (метод partedit)

# ★ ТОЛЬКО ОДНА КОПИЯ — ЭТО СОЗНАТЕЛЬНОЕ ОТСТУПЛЕНИЕ ОТ ПРАВИЛА.
# В ISO-профиле НЕТ ни partedit.py, ни diskmap.py, а partitioning.py там —
# копия от 24 июля (очередь v19, пункт 7). Патчить трёхнедельный слепок
# бессмысленно и вредно: получится ощущение «обе копии в строю», которого
# нет. Профиль синхронизируется ЦЕЛИКОМ через rsync перед сборкой.
ROOTS = [
    os.path.expanduser("~/pzhavos/installer"),
]

STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


# ══════════════════════════════════════════════════════════════════════
#  1. i18n.py
# ══════════════════════════════════════════════════════════════════════

I18N_ANCHOR_HINT = '''        "ru": "Что уже есть на диске. Красным помечено то, что удалять нельзя:\\n"
              "загрузчик Windows, служебные разделы и разделы восстановления.\\n"
              "Пока это окно только показывает разделы — изменение появится позже.",
        "en": "What is already on the disk. Red marks what must not be deleted:\\n"
              "the Windows bootloader, service and recovery partitions.\\n"
              "For now this window only shows partitions — editing comes later.",'''

I18N_NEW_HINT = '''        "ru": "Что уже есть на диске. Красным помечено то, что удалять нельзя:\\n"
              "загрузчик Windows, служебные разделы и разделы восстановления.\\n"
              "Выбери строку — снизу будет написано, что с ней можно сделать.",
        "en": "What is already on the disk. Red marks what must not be deleted:\\n"
              "the Windows bootloader, service and recovery partitions.\\n"
              "Select a row — the line below tells you what you can do with it.",'''

I18N_ANCHOR_TAIL = '''    "pe_no_data": {
        "ru": "Не удалось прочитать таблицу разделов.\\n"
              "Обычно это нехватка прав: parted требует root.",
        "en": "Could not read the partition table.\\n"
              "Usually a permissions issue: parted needs root.",
    },
'''

I18N_ADD = '''    "pe_no_data": {
        "ru": "Не удалось прочитать таблицу разделов.\\n"
              "Обычно это нехватка прав: parted требует root.",
        "en": "Could not read the partition table.\\n"
              "Usually a permissions issue: parted needs root.",
    },

    # --- сессия 4: запись на диск ---
    "pe_ro": {"ru": "Изменять разделы нельзя: %s", "en": "Editing is not possible: %s"},
    "pe_pick_part": {"ru": "Сначала выбери раздел в таблице.", "en": "Select a partition first."},
    "pe_pick_free": {"ru": "Сначала выбери свободное место (бирюзовая строка).",
                     "en": "Select free space first (the teal row)."},
    "pe_confirm_title": {"ru": "Удалить раздел?", "en": "Delete partition?"},
    "pe_confirm_text": {
        "ru": "Будет удалён:\\n\\n%s\\n\\n"
              "Все данные на нём пропадут безвозвратно.\\n"
              "Отменить это действие уже нельзя.",
        "en": "About to delete:\\n\\n%s\\n\\n"
              "All data on it will be lost for good.\\n"
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
        "ru": "Точку монтирования назначишь на предыдущем экране.\\n"
              "Для раздела EFI выбери fat32 — флаг загрузки поставится сам.",
        "en": "Mount points are assigned on the previous screen.\\n"
              "For an EFI partition pick fat32 — the boot flag is set automatically.",
    },
    "pe_bad_size": {"ru": "Не понимаю размер «%s». Примеры: 512M, 40G, 1.5G.",
                    "en": "Cannot read the size “%s”. Examples: 512M, 40G, 1.5G."},
    "pe_size_big": {"ru": "Это больше, чем свободно здесь (%s).",
                    "en": "That is more than the free space here (%s)."},
    "pe_size_small": {"ru": "Слишком мало — нужно хотя бы %s.",
                      "en": "Too small — at least %s is needed."},
'''


# ══════════════════════════════════════════════════════════════════════
#  2. partedit.py
# ══════════════════════════════════════════════════════════════════════

PE_A_OLD = '''from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

import diskmap
from i18n import tr
'''

PE_A_NEW = '''from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

import diskmap
import partops
from i18n import tr

# Порядок в выпадашке — от самого частого к редкому. None = без ФС.
FS_CHOICES = (
    ("ext4", "ext4"),
    ("fat32", "fat32 (EFI / флешки)"),
    ("btrfs", "btrfs"),
    ("xfs", "xfs"),
    ("f2fs", "f2fs"),
    ("linux-swap", "swap"),
    (None, None),          # подпись подставляется из i18n на месте
)

_UNITS = {"k": 1024, "m": 1024 ** 2, "g": 1024 ** 3, "t": 1024 ** 4}


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
    try:
        val = float(s)
    except ValueError:
        return None
    if val <= 0:
        return None
    return int(val * mult)
'''

PE_B_OLD = '''        self.btn_del = QPushButton(tr("pe_delete"))
        self.btn_new = QPushButton(tr("pe_create"))
        for b in (self.btn_del, self.btn_new):
            b.setEnabled(False)          # сессия 3
            b.setToolTip(tr("pe_soon"))
'''

PE_B_NEW = '''        self.btn_del = QPushButton(tr("pe_delete"))
        self.btn_del.clicked.connect(self._do_delete)
        self.btn_new = QPushButton(tr("pe_create"))
        self.btn_new.clicked.connect(self._do_create)
'''

PE_C_OLD = '''        v.addLayout(row)

        self.reload()
'''

PE_C_NEW = '''        v.addLayout(row)

        # Гейт записи. Вычисляется на каждый reload(): условия (root,
        # /run/archiso, режим стенда) в принципе могут измениться между
        # открытиями окна, а стоит проверка копейки.
        self.can_write = False
        self.why_ro = ""
        self.reload()
'''

PE_D_OLD = '''    # --- данные ---
    def reload(self):
        m, ctx, sample = read_all(self.disk)
        self.stand.setVisible(bool(sample))
'''

PE_D_NEW = '''    # --- данные ---
    def reload(self):
        self.can_write, self.why_ro = partops.write_allowed(self.disk)
        m, ctx, sample = read_all(self.disk)
        self.stand.setVisible(bool(sample))
'''

PE_E_OLD = '''    # --- реакция на выбор строки (уровень 1 ТЗ 5.4) ---
    def _selection_changed(self):
        it = self.current_item()
        if it is None:
            self._say(tr("pe_select"), MUTED)
            return
        ok, why = diskmap.can_delete(it, self.ctx)
        if ok:
            self._say(tr("pe_can_delete"), MUTED)
        else:
            self._say(tr("pe_cant_delete") % why, CORAL)
'''

PE_E_NEW = '''    # --- реакция на выбор строки (уровень 1 ТЗ 5.4) ---
    def _selection_changed(self):
        it = self.current_item()
        self._sync_buttons(it)
        if it is None:
            self._say(tr("pe_select"), MUTED)
            return
        if it["kind"] == "free":
            self._say(tr("pe_select"), MUTED)
            return
        ok, why = diskmap.can_delete(it, self.ctx)
        if ok:
            self._say(tr("pe_can_delete"), MUTED)
        else:
            self._say(tr("pe_cant_delete") % why, CORAL)

    def _sync_buttons(self, it):
        """Кнопка активна ТОЛЬКО когда операция реально пройдёт.

        Серая кнопка с внятной подсказкой честнее активной, которая
        отвечает отказом. Гейт записи — первая причина, тип строки —
        вторая, запрет can_delete — третья.
        """
        if not self.can_write:
            for b in (self.btn_del, self.btn_new):
                b.setEnabled(False)
                b.setToolTip(tr("pe_ro") % self.why_ro)
            return

        is_part = it is not None and it["kind"] == "part"
        is_free = it is not None and it["kind"] == "free"

        can_del, why_del = (False, "")
        if is_part:
            can_del, why_del = diskmap.can_delete(it, self.ctx)
        self.btn_del.setEnabled(bool(can_del))
        self.btn_del.setToolTip(
            "" if can_del else
            (tr("pe_cant_delete") % why_del) if is_part else tr("pe_pick_part"))

        self.btn_new.setEnabled(is_free)
        self.btn_new.setToolTip("" if is_free else tr("pe_pick_free"))

    # --- операции записи (сессия 4) ---
    def _fail(self, exc):
        QMessageBox.critical(self, tr("pe_err_title"), str(exc))

    def _after_write(self, msg):
        """Кэши protection_map/esp_free после записи ВРУТ — сбросить.
        partops этого не делает сознательно (не тянет PySide6)."""
        forget(self.disk)
        self.reload()
        self._say(msg, TEAL)

    def _busy(self, on):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor) if on \\
            else QApplication.restoreOverrideCursor()
        if on:
            self._say(tr("pe_busy"), MUTED)
        QApplication.processEvents()

    def _do_delete(self):
        it = self.current_item()
        if it is None or it["kind"] != "part":
            return
        ok, why = diskmap.can_delete(it, self.ctx)
        if not ok:
            QMessageBox.warning(self, tr("pe_err_title"),
                                tr("pe_cant_delete") % why)
            return

        # Уровень 3. Описание собирается ЗДЕСЬ, до удаления: partops.delete
        # возвращает его постфактум, для подтверждения это бесполезно.
        label = (f"{it['path']} — {diskmap.human(it['size'])}, "
                 f"{diskmap.describe(it, self.ctx)}")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(tr("pe_confirm_title"))
        box.setText(tr("pe_confirm_text") % label)
        yes = box.addButton(tr("pe_confirm_yes"),
                            QMessageBox.ButtonRole.DestructiveRole)
        no = box.addButton(tr("pe_cancel"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(no)        # по умолчанию — НЕ удалять
        box.exec()
        if box.clickedButton() is not yes:
            return

        # Курсор снимается в finally РАНЬШЕ, чем показывается ошибка:
        # модалка с песочными часами выглядит как зависание.
        self._busy(True)
        err = None
        try:
            gone = partops.delete(self.disk, it["number"])
        except partops.PartOpError as e:
            err = e
        finally:
            self._busy(False)
        if err is not None:
            forget(self.disk)      # операция могла пройти частично
            self.reload()
            self._fail(err)
            return
        self._after_write(tr("pe_done_del") % gone)

    def _do_create(self):
        it = self.current_item()
        if it is None or it["kind"] != "free":
            return
        dlg = CreateDialog(it, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        size, fs = dlg.result_size, dlg.result_fs

        self._busy(True)
        err = None
        try:
            path = partops.create(self.disk, it["start"],
                                  it["start"] + size - 1, fs)
        except partops.PartOpError as e:
            err = e
        finally:
            self._busy(False)
        if err is not None:
            forget(self.disk)      # mkpart мог пройти, а mkfs упасть
            self.reload()
            self._fail(err)
            return
        self._after_write(tr("pe_done_new") % path)
'''

PE_F_OLD = '''    def _say(self, text, color):
        self.status.setText(text)
        self.status.setStyleSheet(f"color:{color}")
'''

PE_F_NEW = '''    def _say(self, text, color):
        self.status.setText(text)
        self.status.setStyleSheet(f"color:{color}")


class CreateDialog(QDialog):
    """Размер + файловая система. Начало берётся из выбранного свободного
    блока, точка монтирования не спрашивается — она на странице разметки.

    Проверка размера здесь — ДЛЯ ЧЕЛОВЕКА (сказать словами, что не так).
    Настоящая проверка живёт в partops.create по свежей карте: эта может
    устареть, пока пользователь думает.
    """

    def __init__(self, free_item, parent=None):
        super().__init__(parent)
        self.item = free_item
        self.avail = int(free_item["size"])
        self.result_size = self.avail
        self.result_fs = "ext4"
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setWindowTitle(tr("pe_new_title"))

        self.ed_size = QLineEdit()
        self.ed_size.setPlaceholderText(tr("pe_new_size_ph"))
        self.cb_fs = QComboBox()
        for key, label in FS_CHOICES:
            self.cb_fs.addItem(tr("pe_new_fs_none") if key is None else label,
                               key)

        avail = QLabel(tr("pe_new_avail") % diskmap.human(self.avail))
        avail.setStyleSheet(f"color:{TEAL}")
        note = QLabel(tr("pe_new_note"))
        note.setStyleSheet(f"color:{MUTED}")
        note.setWordWrap(True)
        self.err = QLabel()
        self.err.setStyleSheet(f"color:{CORAL}")
        self.err.setWordWrap(True)

        form = QFormLayout()
        form.addRow(tr("pe_new_size"), self.ed_size)
        form.addRow(tr("pe_new_fs"), self.cb_fs)

        bb = QDialogButtonBox()
        self.btn_ok = bb.addButton(tr("pe_new_ok"),
                                   QDialogButtonBox.ButtonRole.AcceptRole)
        bb.addButton(tr("pe_cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)

        v = QVBoxLayout(self)
        v.addWidget(avail)
        v.addLayout(form)
        v.addWidget(note)
        v.addWidget(self.err)
        v.addWidget(bb)

    def _accept(self):
        raw = self.ed_size.text().strip()
        if raw:
            size = parse_size(raw)
            if size is None:
                self.err.setText(tr("pe_bad_size") % raw)
                return
            if size > self.avail:
                self.err.setText(tr("pe_size_big")
                                 % diskmap.human(self.avail))
                return
        else:
            size = self.avail
        if size < partops.MIN_CREATE:
            self.err.setText(tr("pe_size_small")
                             % diskmap.human(partops.MIN_CREATE))
            return
        self.result_size = size
        self.result_fs = self.cb_fs.currentData()
        self.accept()
'''

PLAN = [
    ("i18n.py", [(I18N_ANCHOR_HINT, I18N_NEW_HINT),
                 (I18N_ANCHOR_TAIL, I18N_ADD)]),
    ("partedit.py", [(PE_A_OLD, PE_A_NEW), (PE_B_OLD, PE_B_NEW),
                     (PE_C_OLD, PE_C_NEW), (PE_D_OLD, PE_D_NEW),
                     (PE_E_OLD, PE_E_NEW), (PE_F_OLD, PE_F_NEW)]),
]


def process(root, dry):
    """Возвращает {путь: новый_текст} либо кидает AssertionError."""
    out = {}
    for fname, pairs in PLAN:
        path = os.path.join(root, fname)
        if not os.path.exists(path):
            print(f"    ПРОПУСК: нет {path}")
            continue
        src = open(path, encoding="utf-8").read()
        mark = MARK if fname == "i18n.py" else MARK_PE
        if mark in src:
            print(f"    уже применён: {fname}")
            continue
        for old, new in pairs:
            n = src.count(old)
            assert n == 1, (f"{path}: якорь встречается {n} раз, ожидался 1.\n"
                            f"--- ЯКОРЬ ---\n{old[:200]}")
            src = src.replace(old, new, 1)
        out[path] = src
        print(f"    готов к записи: {fname}  ({len(src.encode("utf-8"))} байт)")
    return out


def main():
    print(f"patch_session4  {STAMP}")
    staged = {}
    for root in ROOTS:
        print(f"\n[{root}]")
        if not os.path.isdir(root):
            print("    ПРОПУСК: каталога нет")
            continue
        staged.update(process(root, dry=True))

    if not staged:
        print("\nНечего делать — патч уже применён или файлов нет.")
        return 0

    # Компиляция ДО записи: битый Python не должен попасть в дерево.
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
    print("\npy_compile: все файлы валидны")

    for path, text in staged.items():
        bak = f"{path}.s4bak-{STAMP}"
        with open(bak, "w", encoding="utf-8") as f:
            f.write(open(path, encoding="utf-8").read())
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"записан {path}  (бэкап {os.path.basename(bak)})")

    print("\nГОТОВО.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
