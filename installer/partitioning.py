"""Страница «Разметка»: два режима — стереть диск или разложить вручную.

Вынесено отдельным файлом, чтобы не трогать проверенный pages.py.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from config_gen import (
    FILESYSTEMS, MANUAL_FILESYSTEMS, MOUNTPOINTS, detect_sector_size, is_uefi,
    list_partitions, max_root_gib, use_separate_home, use_subvols,
)
from i18n import tr
from pages import BasePage

CORAL = "#c67573"
TEAL = "#5fd3c8"
MUTED = "#a0a0a0"


class ManualRow(QWidget):
    """Строка таблицы ручной разметки: раздел -> точка монтирования + формат."""

    def __init__(self, part: dict, on_change):
        super().__init__()
        self.part = part
        self.on_change = on_change

        size_gib = int(part.get("size") or 0) / 2 ** 30
        cur_fs = part.get("raw_fs") or part.get("cur_fs") or "—"
        self.info = QLabel(f'{part["path"]}   {size_gib:.1f} GiB   {cur_fs}')
        self.info.setMinimumWidth(280)

        self.mount = QComboBox()
        self.mount.addItem(tr("part_mount_none"), None)
        for mp in MOUNTPOINTS:
            self.mount.addItem(mp, mp)
        self.mount.setFixedWidth(120)
        self.mount.currentIndexChanged.connect(self._changed)

        self.fmt = QCheckBox(tr("part_col_format"))
        self.fmt.toggled.connect(self._changed)

        self.fs = QComboBox()
        self.fs.addItems(MANUAL_FILESYSTEMS)
        self.fs.setFixedWidth(90)
        self.fs.currentTextChanged.connect(self._changed)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 2, 0, 2)
        row.addWidget(self.info)
        row.addWidget(self.mount)
        row.addWidget(self.fmt)
        row.addWidget(self.fs)
        row.addStretch()
        self._changed()

    def _changed(self) -> None:
        mp = self.mount.currentData()
        self.part["mountpoint"] = mp

        # swap форматируется всегда (mkswap), выбор ФС не нужен
        if mp == "swap":
            self.fmt.setChecked(True)
            self.fmt.setEnabled(False)
            self.fs.setEnabled(False)
        elif mp == "/boot" and is_uefi():
            # ESP обязан быть FAT — иначе прошивка его не прочитает
            self.fs.setCurrentText("fat32")
            self.fs.setEnabled(False)
            self.fmt.setEnabled(True)
            if not self.part.get("cur_fs", "").startswith("fat"):
                self.fmt.setChecked(True)
                self.fmt.setEnabled(False)
        else:
            self.fmt.setEnabled(mp is not None)
            # Нечего сохранять, если ФС не распознана — форматирование обязательно
            if mp is not None and not self.part.get("cur_fs"):
                self.fmt.setChecked(True)
                self.fmt.setEnabled(False)
            self.fs.setEnabled(mp is not None and self.fmt.isChecked())

        self.part["format"] = self.fmt.isChecked()
        self.part["fs"] = self.fs.currentText()
        self.on_change()


class PartitioningPage(BasePage):
    def __init__(self, state: dict):
        super().__init__(state)
        state.setdefault("part_mode", "wipe")
        state.setdefault("fs", "ext4")
        state.setdefault("btrfs_subvols", True)
        state.setdefault("btrfs_compress", True)
        state.setdefault("separate_home", False)
        state.setdefault("root_size_gib", 40)
        state.setdefault("luks", False)
        state.setdefault("luks_password", "")
        state.setdefault("luks_password2", "")
        state.setdefault("manual_parts", [])
        state.setdefault("sector_size", 512)

        # --- выбор режима ---
        self.rb_wipe = QRadioButton()
        self.rb_manual = QRadioButton()
        grp = QButtonGroup(self)
        grp.addButton(self.rb_wipe)
        grp.addButton(self.rb_manual)
        self.rb_wipe.setChecked(state["part_mode"] == "wipe")
        self.rb_manual.setChecked(state["part_mode"] == "manual")
        self.rb_wipe.toggled.connect(self._mode_changed)

        self.fw_label = QLabel()
        self.fw_label.setObjectName("muted")

        mode_row = QHBoxLayout()
        mode_row.addWidget(self.rb_wipe)
        mode_row.addSpacing(20)
        mode_row.addWidget(self.rb_manual)
        mode_row.addStretch()
        mode_row.addWidget(self.fw_label)

        self.body.addLayout(mode_row)
        self.body.addSpacing(8)
        self.body.addWidget(self._build_wipe_box())
        self.body.addWidget(self._build_manual_box(), 1)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.RichText)
        self.body.addSpacing(8)
        self.body.addWidget(self.summary)

        self.retranslate()
        self._mode_changed()

    # --- блок «Стереть диск» ---
    def _build_wipe_box(self) -> QWidget:
        self.wipe_box = QGroupBox()
        form = QFormLayout(self.wipe_box)
        self.form = form
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)

        self.fs_combo = QComboBox()
        self.fs_combo.addItems(FILESYSTEMS)
        self.fs_combo.setCurrentText(self.state.get("fs", "ext4"))
        self.fs_combo.setFixedWidth(160)
        self.fs_combo.currentTextChanged.connect(self._store_wipe)

        self.cb_subvols = QCheckBox()
        self.cb_subvols.setChecked(self.state.get("btrfs_subvols", True))
        self.cb_subvols.toggled.connect(self._store_wipe)

        self.cb_compress = QCheckBox()
        self.cb_compress.setChecked(self.state.get("btrfs_compress", True))
        self.cb_compress.toggled.connect(self._store_wipe)

        self.cb_home = QCheckBox()
        self.cb_home.setChecked(self.state.get("separate_home", False))
        self.cb_home.toggled.connect(self._store_wipe)

        self.root_size = QSpinBox()
        self.root_size.setRange(15, 4096)
        self.root_size.setSuffix(" GiB")
        self.root_size.setValue(int(self.state.get("root_size_gib") or 40))
        self.root_size.setFixedWidth(160)
        self.root_size.valueChanged.connect(self._store_wipe)

        self.cb_luks = QCheckBox()
        self.cb_luks.setChecked(self.state.get("luks", False))
        self.cb_luks.toggled.connect(self._store_wipe)

        self.luks_pass = QLineEdit()
        self.luks_pass2 = QLineEdit()
        for w in (self.luks_pass, self.luks_pass2):
            w.setEchoMode(QLineEdit.EchoMode.Password)
            w.setFixedWidth(240)
        self.luks_pass.textChanged.connect(self._store_wipe)
        self.luks_pass2.textChanged.connect(self._store_wipe)

        self.luks_note = QLabel()
        self.luks_note.setObjectName("muted")
        self.luks_note.setWordWrap(False)

        self.l_fs, self.l_root, self.l_luks1, self.l_luks2 = (QLabel() for _ in range(4))
        form.addRow(self.l_fs, self.fs_combo)
        form.addRow(QLabel(), self.cb_subvols)
        form.addRow(QLabel(), self.cb_compress)
        form.addRow(QLabel(), self.cb_home)
        form.addRow(self.l_root, self.root_size)
        form.addRow(QLabel(), self.cb_luks)
        form.addRow(self.l_luks1, self.luks_pass)
        form.addRow(self.l_luks2, self.luks_pass2)
        form.addRow(QLabel(), self.luks_note)
        return self.wipe_box

    # --- блок «Вручную» ---
    def _build_manual_box(self) -> QWidget:
        self.manual_box = QGroupBox()
        v = QVBoxLayout(self.manual_box)

        self.manual_hint = QLabel()
        self.manual_hint.setObjectName("muted")
        self.manual_hint.setWordWrap(True)

        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self._reload_parts)
        top = QHBoxLayout()
        top.addWidget(self.manual_hint, 1)
        top.addWidget(self.refresh_btn)

        self.rows_box = QVBoxLayout()
        holder = QWidget()
        holder.setLayout(self.rows_box)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(holder)

        self.no_parts = QLabel()
        self.no_parts.setObjectName("muted")

        v.addLayout(top)
        v.addWidget(self.no_parts)
        v.addWidget(scroll, 1)
        return self.manual_box

    # --- логика ---
    def on_enter(self) -> None:
        disk = self.state.get("disk")
        if disk:
            self.state["sector_size"] = detect_sector_size(disk)
        self._reload_parts()
        self._store_wipe()

    def _reload_parts(self) -> None:
        while self.rows_box.count():
            item = self.rows_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        disk = self.state.get("disk")
        parts = list_partitions(disk) if disk else []
        self.state["manual_parts"] = parts
        self.no_parts.setVisible(not parts)
        for p in parts:
            self.rows_box.addWidget(ManualRow(p, self._update_summary))
        self.rows_box.addStretch()
        self._update_summary()

    def _mode_changed(self) -> None:
        wipe = self.rb_wipe.isChecked()
        self.state["part_mode"] = "wipe" if wipe else "manual"
        self.wipe_box.setVisible(wipe)
        self.manual_box.setVisible(not wipe)
        self._update_summary()

    def _store_wipe(self) -> None:
        s = self.state
        s["fs"] = self.fs_combo.currentText()
        s["btrfs_subvols"] = self.cb_subvols.isChecked()
        s["btrfs_compress"] = self.cb_compress.isChecked()
        s["separate_home"] = self.cb_home.isChecked()
        s["root_size_gib"] = self.root_size.value()
        s["luks"] = self.cb_luks.isChecked()
        s["luks_password"] = self.luks_pass.text()
        s["luks_password2"] = self.luks_pass2.text()

        btrfs = s["fs"] == "btrfs"
        # setRowVisible убирает и строку формы; setVisible оставлял бы дыру
        self.form.setRowVisible(self.cb_subvols, btrfs)
        self.form.setRowVisible(self.cb_compress, btrfs)
        self.form.setRowVisible(self.cb_home, not use_subvols(s))
        self.form.setRowVisible(self.root_size, use_separate_home(s))
        for w in (self.luks_pass, self.luks_pass2, self.luks_note):
            self.form.setRowVisible(w, s["luks"])
        # При сабволюмах @home заменяет отдельный раздел — так делает archinstall

        self.root_size.setMaximum(max(max_root_gib(s), 15))

        self._update_summary()

    def _update_summary(self) -> None:
        s = self.state
        disk = s.get("disk_desc") or s.get("disk") or tr("not_set")

        if s.get("part_mode") == "manual":
            rows = []
            for p in s.get("manual_parts") or []:
                if not p.get("mountpoint"):
                    continue
                act = tr("part_will_format") if p.get("format") else tr("part_will_keep")
                fs = p["fs"] if p.get("format") else (p.get("cur_fs") or "—")
                rows.append(f'{p["path"]} → {p["mountpoint"]} ({act}, {fs})')
            if not rows:
                html = f'<p style="color:{CORAL}">⚠ {tr("err_no_root")}</p>'
            else:
                body = "<br>".join(rows)
                html = (
                    f'<p style="color:{TEAL};font-weight:600">{tr("part_summary")}</p>'
                    f'<p style="color:{MUTED}">{body}</p>'
                )
        else:
            fs = s.get("fs", "ext4")
            bits = [f'/boot 1 GiB fat32', f'/ {fs}']
            if use_subvols(s):
                bits.append("@, @home, @log, @pkg")
            if use_separate_home(s):
                bits[1] = f'/ {fs} {s["root_size_gib"]} GiB'
                bits.append(f'/home {fs}')
            if s.get("luks"):
                bits.append("LUKS")
            bits.append("UEFI/GPT" if is_uefi() else "BIOS/MBR")
            html = (
                f'<p style="color:{CORAL};font-weight:700">⚠ {tr("part_wipe_warn")} {disk}</p>'
                f'<p style="color:{MUTED}">{" · ".join(bits)}</p>'
            )

        self.summary.setText(html)
        s["part_desc"] = self._plain_desc()

    def _plain_desc(self) -> str:
        s = self.state
        if s.get("part_mode") == "manual":
            n = len([p for p in s.get("manual_parts") or [] if p.get("mountpoint")])
            return f'{tr("part_mode_manual")} — {n} {tr("part_count")}'
        parts = [tr("part_mode_wipe"), s.get("fs", "ext4")]
        if use_subvols(s):
            parts.append("subvols")
        if use_separate_home(s):
            parts.append(f'/home, / {s["root_size_gib"]} GiB')
        if s.get("luks"):
            parts.append("LUKS")
        return " · ".join(parts)

    def retranslate(self) -> None:
        self.title.setText(tr("part_title"))
        self.rb_wipe.setText(tr("part_mode_wipe"))
        self.rb_manual.setText(tr("part_mode_manual"))
        self.fw_label.setText("UEFI" if is_uefi() else "BIOS (Legacy)")
        self.wipe_box.setTitle(tr("part_mode_wipe"))
        self.manual_box.setTitle(tr("part_mode_manual"))
        self.l_fs.setText(tr("part_fs"))
        self.cb_subvols.setText(tr("part_subvols"))
        self.cb_compress.setText(tr("part_compress"))
        self.cb_home.setText(tr("part_sep_home"))
        self.l_root.setText(tr("part_root_size"))
        self.cb_luks.setText(tr("part_luks"))
        self.l_luks1.setText(tr("part_luks_pass"))
        self.l_luks2.setText(tr("part_luks_pass2"))
        self.luks_note.setText(tr("part_luks_note"))
        self.manual_hint.setText(tr("part_manual_hint"))
        self.refresh_btn.setText(tr("refresh"))
        self.no_parts.setText(tr("part_no_parts"))
