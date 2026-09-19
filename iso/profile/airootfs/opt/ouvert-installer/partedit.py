"""partedit.py — модальный диалог «Изменить разделы…» (этап 5, шаг 3).
ВЕРСИЯ 2: + карта защиты для страницы разметки (Bug 31) и замер ESP (Bug 23).

СЕССИЯ 2: ТОЛЬКО ЧТЕНИЕ. Ни одной операции записи на диск.
Кнопки «Удалить»/«Создать» показаны, но неактивны — операции появятся
в сессии 3. Показаны сразу, чтобы потом не перекладывать компоновку.

РЕЖИМ СТЕНДА (отладка GUI без root; parted требует root, а запускать
установщик под sudo на рабочей машине нельзя — build_context ro-монтирует
каждый ESP, включая живой /boot хоста):
    OUVERT_DISKMAP_SAMPLE=tests/sample_t26.txt   слепок вместо реального диска
    OUVERT_DISKMAP_MSBOOT=/dev/vda1              какие ESP считать виндовыми
    OUVERT_DISKMAP_MOUNTED=/dev/vda7=/           какие разделы «примонтированы»
    OUVERT_DISKMAP_ESPFREE=/dev/vda1=2048        сколько байт «свободно» на ESP
Последние три действуют ТОЛЬКО вместе с первым. В режиме стенда
в окне горит красная плашка — стенд нельзя спутать с реальным диском.
Если файл слепка не читается, показываем ошибку, а НЕ уходим на живой
диск: стенд обязан оставаться стендом (fail-closed).
"""

import os

from PySide6.QtCore import Qt
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

# Bug 37б: интерфейс пишет «3.5 ГиБ» кириллицей, человек копирует то, что
# видит. Отказать ему за это — издевательство.
_CYR = {"к": "k", "м": "m", "г": "g", "т": "t", "б": "b", "и": "i"}

# Bug 37а: human() округляет ВВЕРХ, поэтому показанный размер бывает
# на несколько КиБ больше настоящего. Допуск в 1 МиБ закрывает щель.
# Риска нет: partops.align_range всё равно режет конец ВНИЗ до границы.
SLACK = 1024 * 1024


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
    try:
        val = float(s)
    except ValueError:
        return None
    if val <= 0:
        return None
    return int(val * mult)

CORAL = "#c67573"
TEAL = "#5fd3c8"
MUTED = "#a0a0a0"

COLS = ("pe_col_num", "pe_col_start", "pe_col_size", "pe_col_fs",
        "pe_col_name", "pe_col_flags", "pe_col_what")

EMPTY = {"disk": None, "items": []}

# Кэши: ro-монтирование чужого ESP — дорогая операция, а _update_summary
# дёргается на каждое шевеление комбобокса.
_PROTECT_CACHE = {}
_FREE_CACHE = {}


def _env_list(name):
    return {x.strip() for x in os.environ.get(name, "").split(",") if x.strip()}


def _env_pairs(name):
    out = {}
    for pair in os.environ.get(name, "").split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def load_map(disk):
    """Возвращает (карта, путь_слепка|None). В режиме стенда диск не трогается."""
    sample = os.environ.get("OUVERT_DISKMAP_SAMPLE")
    if not sample:
        return diskmap.read_disk(disk), None
    try:
        with open(sample, encoding="utf-8") as f:
            return diskmap.parse_parted(f.read()), sample
    except OSError:
        return dict(EMPTY), sample


def make_context(m, sample):
    if not sample:
        return diskmap.build_context(m)
    ms = _env_list("OUVERT_DISKMAP_MSBOOT")
    return diskmap.build_context(m, probe=lambda dev: dev in ms)


def apply_mounted(m, sample):
    """item['mounted'] — вход для can_delete (ТЗ 5.7)."""
    if not sample:
        diskmap.fill_mounted(m)
        return
    fake = _env_pairs("OUVERT_DISKMAP_MOUNTED")
    for it in m.get("items", []):
        if it["kind"] == "part":
            it["mounted"] = fake.get(it["path"], "")


def read_all(disk):
    """Карта + контекст + mounted одним вызовом. Возвращает (m, ctx, sample)."""
    m, sample = load_map(disk)
    if not m.get("disk"):
        return m, {}, sample
    ctx = make_context(m, sample)
    apply_mounted(m, sample)
    return m, ctx, sample


def protection_map(disk, force=False):
    """{путь: причина} — разделы, которые НЕЛЬЗЯ форматировать (Bug 31).

    Возвращает (карта, читалось_ли_успешно). Второй элемент важен: пустая
    карта из-за нехватки прав и пустая карта на чистом диске — разные
    вещи, и молча считать «защищать нечего» нельзя.
    """
    if not force and disk in _PROTECT_CACHE:
        return _PROTECT_CACHE[disk]
    m, ctx, _ = read_all(disk)
    if not m.get("disk"):
        res = ({}, False)
    else:
        out = {}
        for it in m["items"]:
            if it["kind"] != "part":
                continue
            ok, why = diskmap.can_format(it, ctx)
            if not ok:
                out[it["path"]] = why
        res = (out, True)
    _PROTECT_CACHE[disk] = res
    return res


def esp_free(dev):
    """Свободно байт на разделе; None — измерить не удалось (Bug 23)."""
    if dev in _FREE_CACHE:
        return _FREE_CACHE[dev]
    if os.environ.get("OUVERT_DISKMAP_SAMPLE"):
        raw = _env_pairs("OUVERT_DISKMAP_ESPFREE").get(dev)
        val = int(raw) if raw and raw.isdigit() else None
    else:
        val = diskmap.free_bytes(dev)
    _FREE_CACHE[dev] = val
    return val


def forget(disk=None):
    """Сбросить кэши — после любой правки таблицы разделов."""
    _FREE_CACHE.clear()
    if disk is None:
        _PROTECT_CACHE.clear()
    else:
        _PROTECT_CACHE.pop(disk, None)


class PartitionEditor(QDialog):
    def __init__(self, disk, parent=None):
        super().__init__(parent)
        self.disk = disk
        self.items = []
        self.ctx = {}
        self.setModal(True)
        self.setMinimumSize(880, 480)
        self.setWindowTitle(tr("pe_title") % disk)

        self.stand = QLabel()
        self.stand.setStyleSheet(f"color:{CORAL};font-weight:700")
        self.stand.setVisible(False)

        self.hint = QLabel(tr("pe_hint"))
        self.hint.setStyleSheet(f"color:{MUTED}")
        self.hint.setWordWrap(True)

        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels([tr(c) for c in COLS])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._selection_changed)

        self.status = QLabel()
        self.status.setWordWrap(True)

        self.btn_del = QPushButton(tr("pe_delete"))
        self.btn_del.clicked.connect(self._do_delete)
        self.btn_new = QPushButton(tr("pe_create"))
        self.btn_new.clicked.connect(self._do_create)
        # Bug 42: активна только на диске без таблицы разделов.
        self.btn_label = QPushButton(tr("pe_mklabel_btn"))
        self.btn_label.clicked.connect(self._do_mklabel)
        self.btn_label.setEnabled(False)
        self.btn_reload = QPushButton(tr("refresh"))
        self.btn_reload.clicked.connect(self.reload)
        self.btn_close = QPushButton(tr("pe_close"))
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.accept)

        row = QHBoxLayout()
        row.addWidget(self.btn_del)
        row.addWidget(self.btn_new)
        row.addWidget(self.btn_label)
        row.addStretch()
        row.addWidget(self.btn_reload)
        row.addWidget(self.btn_close)

        v = QVBoxLayout(self)
        v.addWidget(self.stand)
        v.addWidget(self.hint)
        v.addWidget(self.table, 1)
        v.addWidget(self.status)
        v.addLayout(row)

        # Гейт записи. Вычисляется на каждый reload(): условия (root,
        # /run/archiso, режим стенда) в принципе могут измениться между
        # открытиями окна, а стоит проверка копейки.
        self.can_write = False
        self.why_ro = ""
        self.reload()

    # --- данные ---
    def reload(self):
        self.can_write, self.why_ro = partops.write_allowed(self.disk)
        # Bug 46: непустая строка = на диске ФС прямо на устройстве, без
        # таблицы разделов. Сбрасываем на КАЖДОМ reload, до всех ветвлений:
        # значение читает _do_mklabel, и протухшее здесь опаснее пустого.
        self.fs_whole = ""
        m, ctx, sample = read_all(self.disk)
        self.stand.setVisible(bool(sample))
        if sample:
            self.stand.setText(tr("pe_stand") % sample)
        if not m.get("disk"):
            self.items = []
            self.ctx = {}
            self.table.setRowCount(0)
            self._say(tr("pe_no_data"), CORAL)
            return
        self.ctx = ctx
        # Bug 42. parted кладёт тип таблицы в 6-е поле; на голом диске
        # там "unknown", а свободных блоков нет вовсе — без метки понятия
        # "свободное место" не существует. Рисовать его было бы враньём:
        # создать раздел там всё равно нельзя.
        # Bug 46: "loop" — ШЕСТОЙ тип метки, и он тоже означает «таблицы
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
        self.btn_label.setEnabled(False)
        self.items = diskmap.visible_items(m)
        # Bug 43: шапка про «красное» и загрузчик Windows на пустом
        # диске обещает то, чего там нет. Текст — по ситуации.
        has_part = any(i["kind"] == "part" for i in self.items)
        self.hint.setText(tr("pe_hint") if has_part else tr("pe_hint_empty"))
        self._fill_table()
        self._selection_changed()

    def _fill_table(self):
        self.table.setRowCount(len(self.items))
        for r, it in enumerate(self.items):
            free = it["kind"] == "free"
            what = diskmap.describe(it, self.ctx)
            if it.get("mounted"):
                what += "  ·  " + tr("pe_mounted") % it["mounted"]
            blocked = not diskmap.can_delete(it, self.ctx)[0]
            cells = (
                "—" if free else str(it["number"]),
                diskmap.human(it["start"]),
                diskmap.human(it["size"]),
                "—" if free else (it["fstype"] or "—"),
                it["name"] or "",
                ", ".join(it["flags"]),
                what,
            )
            for c, text in enumerate(cells):
                cell = QTableWidgetItem(text)
                if free:
                    cell.setForeground(QColor(TEAL))
                elif blocked and c == len(cells) - 1:
                    cell.setForeground(QColor(CORAL))
                self.table.setItem(r, c, cell)
        self.table.resizeColumnsToContents()

    # --- реакция на выбор строки (уровень 1 ТЗ 5.4) ---
    def _selection_changed(self):
        it = self.current_item()
        self._sync_buttons(it)
        if it is None:
            self._say(tr("pe_select"), MUTED)
            return
        if it["kind"] == "free":
            self._say(tr("pe_can_create"), MUTED)
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
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor) if on \
            else QApplication.restoreOverrideCursor()
        if on:
            self._say(tr("pe_busy"), MUTED)
        QApplication.processEvents()

    def _do_mklabel(self):
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
        # Bug 45: на loop-диске обещать «данные не пострадают» — ложь.
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
            # Bug 38: dlg.start — единственный источник правды о начале.
            path = partops.create(self.disk, dlg.start,
                                  dlg.start + size - 1, fs)
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

    def current_item(self):
        r = self.table.currentRow()
        if r < 0 or r >= len(self.items):
            return None
        return self.items[r]

    def _say(self, text, color):
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
        # Bug 38: и «Доступно», и будущий конец — от ВЫРОВНЕННОГО начала.
        self.start, self.avail = eff_range(free_item)
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
            if size > self.avail + SLACK:
                self.err.setText(tr("pe_size_big")
                                 % diskmap.human(self.avail))
                return
            # Промах на пару КиБ из-за округления показанного числа —
            # это не «мало места», это наша же цифра вернулась обратно.
            size = min(size, self.avail)
        else:
            size = self.avail
        if size < partops.MIN_CREATE:
            self.err.setText(tr("pe_size_small")
                             % diskmap.human(partops.MIN_CREATE))
            return
        self.result_size = size
        self.result_fs = self.cb_fs.currentData()
        self.accept()
