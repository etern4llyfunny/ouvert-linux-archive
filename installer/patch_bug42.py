#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_bug42.py — этап 5, сессия 6.

ЗАКРЫВАЕТ:
  Bug 42 (БЛОКЕР) — редактор разделов не работает с диском без таблицы
      разделов. parted -m печатает в 6-м поле "unknown", свободных блоков
      не показывает вовсе (без метки понятия "свободный блок" не
      существует). Итог: пустая таблица, обе кнопки серые, тупик.
      ЛЕЧЕНИЕ: детект table == "unknown" в reload(), отдельная кнопка
      «Создать таблицу разделов» и partops.mklabel() за тем же гейтом,
      что create/delete. GPT при UEFI, MBR (msdos) при BIOS.
      ЗАЩИТА: mklabel ОТКАЗЫВАЕТ, если таблица уже есть — иначе кнопка
      превращается в «стереть диск целиком».

  Bug 41 (косметика) — подсказка на странице разметки посылает в gparted,
      которого в live-среде нет, при том что рядом есть своя кнопка.

  Bug 43 (косметика) — шапка диалога обещает «Красным помечено то, что
      удалять нельзя: загрузчик Windows…» на пустом диске, где красного
      нет и быть не может. Текст стал ситуативным: три варианта.

СВОЙСТВА: транзакционный (все якоря проверяются ДО первой записи),
идемпотентный (повторный запуск ничего не делает), с бэкапами,
с compile() перед записью.

ПРАВИТ ТОЛЬКО ~/pzhavos/installer/. Профиль ISO синхронизирует build.sh.
"""

import os
import py_compile
import shutil
import sys
import time

BASE = os.path.expanduser("~/pzhavos/installer")
STAMP = time.strftime("%Y%m%d-%H%M%S")

F_I18N = os.path.join(BASE, "i18n.py")
F_OPS = os.path.join(BASE, "partops.py")
F_EDIT = os.path.join(BASE, "partedit.py")


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


# ─────────────────────────── тексты ───────────────────────────

I18N_ANCHOR = ('    "pe_pick_part": {"ru": "Сначала выбери раздел в таблице.",'
               ' "en": "Select a partition first."},')

I18N_NEW = '''    # --- сессия 6: Bug 42, диск без таблицы разделов ---
    "pe_mklabel_btn": {"ru": "Создать таблицу разделов",
                       "en": "Create partition table"},
    "pe_nolabel": {
        "ru": "На диске %s нет таблицы разделов — он совершенно пустой.\\n"
              "Нажми «Создать таблицу разделов», и появится место "
              "под первый раздел.",
        "en": "Disk %s has no partition table — it is completely blank.\\n"
              "Press “Create partition table” to get free space "
              "for the first partition.",
    },
    "pe_hint_nolabel": {
        "ru": "Диск пустой: на нём нет даже таблицы разделов.\\n"
              "Её надо создать один раз, после этого можно будет "
              "добавлять разделы.",
        "en": "The disk is blank: it has no partition table at all.\\n"
              "Create it once, then you can add partitions.",
    },
    "pe_hint_empty": {
        "ru": "Таблица разделов есть, разделов пока нет.\\n"
              "Выбери строку со свободным местом и нажми "
              "«Создать раздел».",
        "en": "The partition table exists, there are no partitions yet.\\n"
              "Select the free space row and press “Create partition”.",
    },
    "pe_mklabel_title": {"ru": "Создать таблицу разделов?",
                         "en": "Create partition table?"},
    "pe_mklabel_text": {
        "ru": "На диске %s будет создана таблица разделов %s.\\n\\n"
              "Диск сейчас пуст, терять на нём нечего — данные "
              "не пострадают.",
        "en": "A partition table will be created on %s: %s.\\n\\n"
              "The disk is empty, there is nothing to lose — "
              "no data will be harmed.",
    },
    "pe_mklabel_yes": {"ru": "Создать", "en": "Create"},
'''

# --- Bug 41: подсказка про gparted -------------------------------------
G_RU_OLD = "Создай их в gparted или выбери"
G_RU_NEW = "Создай их кнопкой «Изменить разделы…» или выбери"
G_EN_OLD = "Create them in gparted or pick"
G_EN_NEW = "Create them with “Edit partitions…” or pick"

# --- partops.mklabel ---------------------------------------------------
OPS_ANCHOR = "def delete(disk: str, number: int) -> str:"

OPS_NEW = '''def mklabel(disk: str, table: str) -> str:
    """Bug 42. Создать таблицу разделов на диске, где её НЕТ.

    Сознательно НЕ умеет перезаписывать существующую таблицу: mklabel
    поверх живой метки — это молчаливое уничтожение всех разделов, и
    такой кнопки в установщике для новичков быть не должно. Если метка
    уже есть — отказ с объяснением.
    """
    _require(disk)
    if table not in ("gpt", "msdos"):
        raise PartOpError(f"Неизвестный тип таблицы разделов: {table}.")
    m = diskmap.read_disk(disk)
    cur = (m.get("disk") or {}).get("table", "")
    if cur and cur != "unknown":
        raise PartOpError(
            f"На {disk} уже есть таблица разделов ({cur}). "
            f"Создание новой стёрло бы все разделы — операция отменена."
        )
    _run(["parted", "-s", disk, "mklabel", table],
         "Создание таблицы разделов")
    _settle()
    return f"{disk}: создана таблица разделов {table}."


'''

# --- partedit: кнопка --------------------------------------------------
E_BTN_ANCHOR = '        self.btn_reload = QPushButton(tr("refresh"))'
E_BTN_NEW = '''        # Bug 42: активна только на диске без таблицы разделов.
        self.btn_label = QPushButton(tr("pe_mklabel_btn"))
        self.btn_label.clicked.connect(self._do_mklabel)
        self.btn_label.setEnabled(False)
'''

E_ROW_ANCHOR = "        row.addWidget(self.btn_new)"
E_ROW_NEW = "        row.addWidget(self.btn_label)\n"

# --- partedit: ветка в reload() ---------------------------------------
E_CTX_ANCHOR = "        self.ctx = ctx"
E_CTX_NEW = '''        # Bug 42. parted кладёт тип таблицы в 6-е поле; на голом диске
        # там "unknown", а свободных блоков нет вовсе — без метки понятия
        # "свободное место" не существует. Рисовать его было бы враньём:
        # создать раздел там всё равно нельзя.
        if (m.get("disk") or {}).get("table", "") in ("unknown", ""):
            self.items = []
            self.table.setRowCount(0)
            self.hint.setText(tr("pe_hint_nolabel"))
            self.btn_del.setEnabled(False)
            self.btn_new.setEnabled(False)
            self.btn_label.setEnabled(self.can_write)
            self.btn_label.setToolTip("" if self.can_write else self.why_ro)
            self._say(tr("pe_nolabel") % self.disk, CORAL)
            return
        self.btn_label.setEnabled(False)
'''

# --- partedit: ситуативная шапка (Bug 43) ------------------------------
E_ITEMS_ANCHOR = "        self.items = diskmap.visible_items(m)"
E_ITEMS_NEW = '''        # Bug 43: шапка про «красное» и загрузчик Windows на пустом
        # диске обещает то, чего там нет. Текст — по ситуации.
        has_part = any(i["kind"] == "part" for i in self.items)
        self.hint.setText(tr("pe_hint") if has_part else tr("pe_hint_empty"))
'''

# --- partedit: обработчик ---------------------------------------------
E_DO_ANCHOR = "    def _do_delete(self):"
E_DO_NEW = '''    def _do_mklabel(self):
        """Bug 42. Тип таблицы НЕ спрашиваем: выбор определяется прошивкой
        живой системы, и предлагать новичку MBR под UEFI — это предлагать
        ему несовместимую с загрузкой конфигурацию."""
        if not self.can_write:
            QMessageBox.warning(self, tr("pe_err_title"),
                                tr("pe_ro") % self.why_ro)
            return
        try:
            from config_gen import is_uefi
            uefi = is_uefi()
        except Exception:
            uefi = os.path.exists("/sys/firmware/efi")
        table = "gpt" if uefi else "msdos"
        shown = "GPT" if uefi else "MBR"

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(tr("pe_mklabel_title"))
        box.setText(tr("pe_mklabel_text") % (self.disk, shown))
        yes = box.addButton(tr("pe_mklabel_yes"),
                            QMessageBox.ButtonRole.AcceptRole)
        box.addButton(tr("pe_cancel"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not yes:
            return

        self._busy(True)
        try:
            msg = partops.mklabel(self.disk, table)
        except Exception as exc:
            self._busy(False)
            self._fail(exc)
            self.reload()
            return
        self._busy(False)
        self._after_write(msg)

'''


def main():
    i18n = read(F_I18N)
    ops = read(F_OPS)
    edit = read(F_EDIT)

    done = ('"pe_mklabel_btn"' in i18n and "def mklabel(" in ops
            and "_do_mklabel" in edit)
    if done:
        print("Патч уже применён — ничего не делаю.")
        return

    # --- проверка ВСЕХ якорей ДО первой записи ---
    need(i18n, I18N_ANCHOR, F_I18N)
    need(i18n, G_RU_OLD, F_I18N)
    need(i18n, G_EN_OLD, F_I18N)
    need(ops, OPS_ANCHOR, F_OPS)
    need(edit, E_BTN_ANCHOR, F_EDIT)
    need(edit, E_ROW_ANCHOR, F_EDIT)
    need(edit, E_CTX_ANCHOR, F_EDIT)
    need(edit, E_ITEMS_ANCHOR, F_EDIT)
    need(edit, E_DO_ANCHOR, F_EDIT)
    print("Все девять якорей сошлись.")

    new_i18n = i18n.replace(I18N_ANCHOR, I18N_NEW + I18N_ANCHOR)
    new_i18n = new_i18n.replace(G_RU_OLD, G_RU_NEW)
    new_i18n = new_i18n.replace(G_EN_OLD, G_EN_NEW)

    new_ops = ops.replace(OPS_ANCHOR, OPS_NEW + OPS_ANCHOR)

    new_edit = edit.replace(E_BTN_ANCHOR, E_BTN_NEW + E_BTN_ANCHOR)
    new_edit = new_edit.replace(E_ROW_ANCHOR, E_ROW_ANCHOR + "\n" + E_ROW_NEW.rstrip("\n"))
    new_edit = new_edit.replace(E_CTX_ANCHOR, E_CTX_ANCHOR + "\n" + E_CTX_NEW.rstrip("\n"))
    new_edit = new_edit.replace(E_ITEMS_ANCHOR,
                                E_ITEMS_ANCHOR + "\n" + E_ITEMS_NEW.rstrip("\n"))
    new_edit = new_edit.replace(E_DO_ANCHOR, E_DO_NEW + E_DO_ANCHOR)

    # --- компиляция ДО записи ---
    for name, src in (("i18n.py", new_i18n), ("partops.py", new_ops),
                      ("partedit.py", new_edit)):
        try:
            compile(src, name, "exec")
        except SyntaxError as e:
            sys.exit(f"РЕЗУЛЬТАТ НЕ КОМПИЛИРУЕТСЯ ({name}): {e}")
    print("Синтаксис всех трёх файлов в порядке.")

    for path, src in ((F_I18N, new_i18n), (F_OPS, new_ops),
                      (F_EDIT, new_edit)):
        bak = f"{path}.b42bak-{STAMP}"
        shutil.copy2(path, bak)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        py_compile.compile(path, doraise=True)
        print(f"OK  {os.path.basename(path)}  "
              f"({len(src.encode('utf-8'))} байт)  бэкап: {os.path.basename(bak)}")

    print("\nГОТОВО. Bug 42, 41, 43.")


if __name__ == "__main__":
    main()
