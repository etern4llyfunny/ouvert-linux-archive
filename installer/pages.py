"""Страницы установщика."""
import json
import re
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton, QRadioButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from desktops import DESKTOP_ENVIRONMENTS, WINDOW_MANAGERS
from i18n import current_lang, set_lang, tr

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

GFX_DRIVERS = [
    "All open-source",
    "AMD / ATI (open-source)",
    "Intel (open-source)",
    "Nvidia (open kernel module for newer GPUs, Turing+)",
    "Nvidia (open-source nouveau driver)",
    "VirtualBox (open-source)",
]


class BasePage(QWidget):
    def __init__(self, state: dict):
        super().__init__()
        self.state = state
        self.title = QLabel()
        self.title.setObjectName("pageTitle")

        self.body = QVBoxLayout()
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 20)
        root.addWidget(self.title)
        root.addSpacing(10)
        root.addLayout(self.body)
        root.addStretch()

    def retranslate(self) -> None:
        pass

    def on_enter(self) -> None:
        pass


class WelcomePage(BasePage):
    lang_changed = Signal()

    def __init__(self, state: dict):
        super().__init__(state)
        self.text = QLabel()
        self.text.setWordWrap(True)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Русский", "ru")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.setFixedWidth(240)
        self.lang_combo.currentIndexChanged.connect(self._on_lang)

        self.body.addWidget(self.text)
        self.body.addSpacing(12)
        self.body.addWidget(self.lang_combo)
        self.retranslate()

    def _on_lang(self) -> None:
        lang = self.lang_combo.currentData()
        self.state["lang"] = lang
        set_lang(lang)
        self.lang_changed.emit()

    def retranslate(self) -> None:
        self.title.setText(tr("welcome_title"))
        self.text.setText(tr("welcome_text"))


class NetworkPage(BasePage):
    """Проводное — просто проверка. Wi-Fi — скан и подключение через iwd."""

    def __init__(self, state: dict):
        super().__init__(state)
        self.state.setdefault("net_ok", False)
        self._busy = False

        self.type_label = QLabel()
        self.rb_wired = QRadioButton()
        self.rb_wifi = QRadioButton()
        grp = QButtonGroup(self)
        grp.addButton(self.rb_wired)
        grp.addButton(self.rb_wifi)
        self.rb_wired.toggled.connect(self._type_changed)

        self.status = QLabel()
        self.status.setWordWrap(True)
        self.check_btn = QPushButton()
        self.check_btn.clicked.connect(self.run_check)

        # --- блок Wi-Fi ---
        self.wifi_box = QWidget()
        wf = QFormLayout(self.wifi_box)
        wf.setHorizontalSpacing(16)
        wf.setVerticalSpacing(10)
        self.l_iface, self.l_ssid, self.l_pass = QLabel(), QLabel(), QLabel()
        self.dev_combo = QComboBox()
        self.dev_combo.setFixedWidth(220)
        row = QHBoxLayout()
        self.net_combo = QComboBox()
        self.net_combo.setMinimumWidth(220)
        self.scan_btn = QPushButton()
        self.scan_btn.clicked.connect(self.scan)
        row.addWidget(self.net_combo, 1)
        row.addWidget(self.scan_btn)
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_edit.setFixedWidth(220)
        self.connect_btn = QPushButton()
        self.connect_btn.clicked.connect(self.wifi_connect)
        wf.addRow(self.l_iface, self.dev_combo)
        wf.addRow(self.l_ssid, row)
        wf.addRow(self.l_pass, self.pass_edit)
        wf.addRow(QLabel(), self.connect_btn)
        self.wifi_box.hide()

        if shutil.which("iwctl") is None:
            self.rb_wifi.setEnabled(False)

        top = QHBoxLayout()
        top.addWidget(self.rb_wired)
        top.addSpacing(20)
        top.addWidget(self.rb_wifi)
        top.addStretch()
        top.addWidget(self.check_btn)

        self.body.addWidget(self.type_label)
        self.body.addLayout(top)
        self.body.addWidget(self.wifi_box)
        self.body.addSpacing(8)
        self.body.addWidget(self.status)
        self.retranslate()

    # --- логика ---
    def on_enter(self) -> None:
        if not self.rb_wired.isChecked() and not self.rb_wifi.isChecked():
            self.rb_wired.setChecked(True)  # вызовет проверку
        elif not self.state.get("net_ok"):
            self.run_check()

    def _type_changed(self) -> None:
        wired = self.rb_wired.isChecked()
        self.wifi_box.setVisible(not wired)
        if wired:
            self.run_check()
        else:
            self._fill_devices()

    def _set_status(self, text: str, ok: bool | None = None) -> None:
        color = {True: "#5fd3c8", False: "#c67573", None: "#a0a0a0"}[ok]
        self.status.setText(text)
        self.status.setStyleSheet(f"color: {color}; font-weight: 600;")

    def run_check(self) -> None:
        if self._busy:
            return
        self._busy = True
        self._set_status(tr("net_checking"))
        self._chk = QProcess(self)
        self._chk.finished.connect(self._check_done)
        self._chk.start("curl", ["-sI", "--max-time", "4", "https://archlinux.org"])

    def _check_done(self, code: int, _s) -> None:
        self._busy = False
        ok = code == 0
        self.state["net_ok"] = ok
        self._set_status(tr("net_ok_msg") if ok else tr("net_fail"), ok)

    def _fill_devices(self) -> None:
        self.dev_combo.clear()
        try:
            out = subprocess.run(
                ["iwctl", "device", "list"], capture_output=True, text=True, timeout=10
            ).stdout
        except Exception:
            out = ""
        for line in _ANSI.sub("", out).splitlines():
            parts = line.split()
            if len(parts) >= 3 and "station" in line:
                self.dev_combo.addItem(parts[0])
        if self.dev_combo.count() == 0:
            self._set_status(tr("net_no_iface"), False)

    def scan(self) -> None:
        dev = self.dev_combo.currentText()
        if not dev:
            self._set_status(tr("net_no_iface"), False)
            return
        subprocess.run(["iwctl", "station", dev, "scan"], capture_output=True)
        self._set_status(tr("net_checking"))
        QTimer.singleShot(2500, self._get_networks)

    def _get_networks(self) -> None:
        dev = self.dev_combo.currentText()
        try:
            out = subprocess.run(
                ["iwctl", "station", dev, "get-networks"],
                capture_output=True, text=True, timeout=10,
            ).stdout
        except Exception:
            out = ""
        self.net_combo.clear()
        seen = set()
        for line in _ANSI.sub("", out).splitlines():
            line = line.strip().lstrip(">").strip()
            if not line or line.startswith(("Available networks", "Network name", "---")):
                continue
            ssid = re.split(r"\s{2,}", line)[0].strip()
            if ssid and ssid not in seen:
                seen.add(ssid)
                self.net_combo.addItem(ssid)
        self._set_status("", None)

    def wifi_connect(self) -> None:
        dev = self.dev_combo.currentText()
        ssid = self.net_combo.currentText()
        if not dev or not ssid:
            return
        self._set_status(tr("net_connecting"))
        args = ["station", dev, "connect", ssid]
        pw = self.pass_edit.text()
        if pw:
            args = ["--passphrase", pw] + args
        self._con = QProcess(self)
        self._con.finished.connect(lambda *_: QTimer.singleShot(2000, self.run_check))
        self._con.start("iwctl", args)

    def retranslate(self) -> None:
        self.title.setText(tr("network_title"))
        self.type_label.setText(tr("net_type"))
        self.rb_wired.setText(tr("net_wired"))
        self.rb_wifi.setText(tr("net_wifi") if self.rb_wifi.isEnabled() else tr("net_wifi") + " — " + tr("net_host_only"))
        self.check_btn.setText(tr("net_check"))
        self.l_iface.setText(tr("net_iface"))
        self.l_ssid.setText(tr("net_ssid"))
        self.l_pass.setText(tr("net_pass"))
        self.scan_btn.setText(tr("net_scan"))
        self.connect_btn.setText(tr("net_connect"))


class TimezonePage(BasePage):
    _FALLBACK = ["Europe/Moscow", "Europe/London", "UTC"]

    def __init__(self, state: dict):
        super().__init__(state)
        try:
            from zoneinfo import available_timezones
            tzs = sorted(
                t for t in available_timezones()
                if "/" in t and not t.startswith(("Etc/", "SystemV/", "US/", "posix", "right"))
            )
        except Exception:
            tzs = [t for t in self._FALLBACK if "/" in t]

        self.regions: dict[str, list[str]] = {}
        for t in tzs:
            region, _, city = t.partition("/")
            self.regions.setdefault(region, []).append(city)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)
        self.l_region, self.l_city = QLabel(), QLabel()
        self.region_combo = QComboBox()
        self.city_combo = QComboBox()
        for w in (self.region_combo, self.city_combo):
            w.setFixedWidth(280)
        self.region_combo.addItems(sorted(self.regions))
        self.region_combo.currentTextChanged.connect(self._fill_cities)
        self.city_combo.currentTextChanged.connect(self._store)
        form.addRow(self.l_region, self.region_combo)
        form.addRow(self.l_city, self.city_combo)
        self.body.addLayout(form)

        tz = self.state.get("timezone") or "Europe/Moscow"
        region, _, city = tz.partition("/")
        if region in self.regions:
            self.region_combo.setCurrentText(region)
            self._fill_cities(region)
            if city in self.regions[region]:
                self.city_combo.setCurrentText(city)
        self.retranslate()

    def _fill_cities(self, region: str) -> None:
        self.city_combo.clear()
        self.city_combo.addItems(self.regions.get(region, []))

    def _store(self, city: str) -> None:
        if city:
            self.state["timezone"] = f"{self.region_combo.currentText()}/{city}"

    def retranslate(self) -> None:
        self.title.setText(tr("tz_title"))
        self.l_region.setText(tr("tz_region"))
        self.l_city.setText(tr("tz_city"))


class DiskPage(BasePage):
    def __init__(self, state: dict):
        super().__init__(state)
        self.warn = QLabel()
        self.warn.setStyleSheet("color: #c67573; font-weight: 600;")
        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self.refresh)
        self.empty = QLabel()
        self.empty.setObjectName("muted")

        self.group = QButtonGroup(self)
        self.list_box = QVBoxLayout()
        holder = QWidget()
        holder.setLayout(self.list_box)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(holder)

        top = QHBoxLayout()
        top.addWidget(self.warn)
        top.addStretch()
        top.addWidget(self.refresh_btn)

        self.body.addLayout(top)
        self.body.addWidget(self.empty)
        self.body.addWidget(scroll)
        self.retranslate()

    def on_enter(self) -> None:
        self.refresh()

    @staticmethod
    def _list_disks() -> list[dict]:
        try:
            out = subprocess.run(
                ["lsblk", "-J", "-d", "-b", "-o", "NAME,SIZE,MODEL,TYPE,PATH,RM"],
                capture_output=True, text=True, timeout=10,
            ).stdout
            devices = json.loads(out).get("blockdevices", [])
        except Exception:
            return []
        return [
            d for d in devices
            if d.get("type") == "disk"
            and not str(d.get("name", "")).startswith(("zram", "fd"))
            and int(d.get("size") or 0) > 0
        ]

    def refresh(self) -> None:
        for b in self.group.buttons():
            self.group.removeButton(b)
        while self.list_box.count():
            item = self.list_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        disks = self._list_disks()
        self.empty.setVisible(not disks)
        selected = self.state.get("disk")
        for d in disks:
            size_gib = int(d.get("size") or 0) / 2**30
            model = (d.get("model") or "").strip()
            rm = "  [USB]" if d.get("rm") else ""
            text = f'{d["path"]}  —  {size_gib:.1f} GiB  {model}{rm}'
            rb = QRadioButton(text)
            rb.toggled.connect(
                lambda on, p=d["path"], t=text, sz=int(d.get("size") or 0): on
                and self.state.update(disk=p, disk_desc=t, disk_size=sz)
            )
            self.group.addButton(rb)
            self.list_box.addWidget(rb)
            if d["path"] == selected:
                rb.setChecked(True)
        self.list_box.addStretch()

    def retranslate(self) -> None:
        self.title.setText(tr("disk_title"))
        self.warn.setText("⚠ " + tr("disk_warn"))
        self.refresh_btn.setText(tr("refresh"))
        self.empty.setText(tr("no_disks"))


class UserPage(BasePage):
    def __init__(self, state: dict):
        super().__init__(state)
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password2 = QLineEdit()
        self.password2.setEchoMode(QLineEdit.EchoMode.Password)
        self.hostname = QLineEdit(self.state.get("hostname", "pzhavos"))

        for w in (self.username, self.password, self.password2, self.hostname):
            w.setFixedWidth(320)

        self.l_user, self.l_pass, self.l_pass2, self.l_host = (QLabel() for _ in range(4))
        form.addRow(self.l_user, self.username)
        form.addRow(self.l_pass, self.password)
        form.addRow(self.l_pass2, self.password2)
        form.addRow(self.l_host, self.hostname)

        self.username.textChanged.connect(lambda t: self.state.update(username=t.strip()))
        self.password.textChanged.connect(lambda t: self.state.update(password=t))
        self.password2.textChanged.connect(lambda t: self.state.update(password2=t))
        self.hostname.textChanged.connect(lambda t: self.state.update(hostname=t.strip()))

        self.body.addLayout(form)
        self.retranslate()

    def retranslate(self) -> None:
        self.title.setText(tr("user_title"))
        self.l_user.setText(tr("username"))
        self.l_pass.setText(tr("password"))
        self.l_pass2.setText(tr("password2"))
        self.l_host.setText(tr("hostname"))


class DesktopPage(BasePage):
    def __init__(self, state: dict):
        super().__init__(state)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        self.de_box = QGroupBox()
        self.wm_box = QGroupBox()
        self._fill(self.de_box, DESKTOP_ENVIRONMENTS)
        self._fill(self.wm_box, WINDOW_MANAGERS)

        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(self.de_box, 1)
        row.addWidget(self.wm_box, 1)

        container = QWidget()
        container.setLayout(row)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        self.body.addWidget(scroll)
        self.retranslate()

    def _fill(self, box: QGroupBox, items: list[tuple[str, str, str]]) -> None:
        lay = QVBoxLayout(box)
        for display, profile, greeter in items:
            rb = QRadioButton(display)
            rb.toggled.connect(
                lambda on, d=display, p=profile, g=greeter: on and self.state.update(
                    profile=p, profile_name=d, greeter=g
                )
            )
            if profile == self.state.get("profile"):
                rb.setChecked(True)
            self.group.addButton(rb)
            lay.addWidget(rb)
        lay.addStretch()

    def retranslate(self) -> None:
        self.title.setText(tr("desktop_title"))
        self.de_box.setTitle(tr("de_group"))
        self.wm_box.setTitle(tr("wm_group"))


class GfxPage(BasePage):
    def __init__(self, state: dict):
        super().__init__(state)
        self.hint = QLabel()
        self.hint.setObjectName("muted")
        self.hint.setWordWrap(True)
        self.body.addWidget(self.hint)
        self.body.addSpacing(8)

        self.group = QButtonGroup(self)
        for drv in GFX_DRIVERS:
            rb = QRadioButton(drv)
            rb.toggled.connect(lambda on, d=drv: on and self.state.update(gfx=d))
            if drv == self.state.get("gfx"):
                rb.setChecked(True)
            self.group.addButton(rb)
            self.body.addWidget(rb)
        self.retranslate()

    def retranslate(self) -> None:
        self.title.setText(tr("gfx_title"))
        self.hint.setText(tr("gfx_hint"))


class ReposPage(BasePage):
    def __init__(self, state: dict):
        super().__init__(state)
        self.note = QLabel()
        self.note.setObjectName("muted")
        self.note.setWordWrap(True)
        self.warn = QLabel()
        self.warn.setObjectName("muted")
        self.warn.setWordWrap(True)

        self.cb_multilib = QCheckBox("multilib")
        self.cb_testing = QCheckBox("testing (core-testing + extra-testing)")
        self.cb_mtesting = QCheckBox("multilib-testing")
        self.cb_multilib.setChecked("multilib" in self.state.get("repos", []))
        for cb in (self.cb_multilib, self.cb_testing, self.cb_mtesting):
            cb.toggled.connect(self._store)

        self.body.addWidget(self.cb_multilib)
        self.body.addWidget(self.note)
        self.body.addSpacing(10)
        self.body.addWidget(self.cb_testing)
        self.body.addWidget(self.cb_mtesting)
        self.body.addWidget(self.warn)
        self.retranslate()

    def _store(self) -> None:
        repos = []
        if self.cb_multilib.isChecked():
            repos.append("multilib")
        if self.cb_testing.isChecked():
            repos.append("testing")
        if self.cb_mtesting.isChecked():
            repos.append("multilib-testing")
        self.state["repos"] = repos

    def retranslate(self) -> None:
        self.title.setText(tr("repo_title"))
        self.note.setText(tr("repo_multilib_note"))
        self.warn.setText("⚠ " + tr("repo_testing_warn"))


class SummaryPage(BasePage):
    def __init__(self, state: dict):
        super().__init__(state)
        self.text = QLabel()
        self.text.setTextFormat(Qt.TextFormat.RichText)
        self.body.addWidget(self.text)
        self.retranslate()

    def on_enter(self) -> None:
        s = self.state
        ns = tr("not_set")
        rows = [
            (tr("lang_label"), "Русский" if s.get("lang") == "ru" else "English"),
            (tr("username"), s.get("username") or ns),
            (tr("hostname"), s.get("hostname") or ns),
            (tr("tz_label"), s.get("timezone") or ns),
            (tr("desktop_label"), s.get("profile_name") or ns),
            (tr("gfx_label"), s.get("gfx") or ns),
            (tr("repos_label"), ", ".join(s.get("repos") or []) or "—"),
            (tr("disk_label"), s.get("disk_desc") or ns),
            (tr("part_label"), s.get("part_desc") or ns),
        ]
        html = "".join(
            f"<p style='margin:6px 0'><span style='color:#c67573'>{k}:</span> {v}</p>"
            for k, v in rows
        )
        self.text.setText(html)

    def retranslate(self) -> None:
        self.title.setText(tr("summary_title"))
        self.on_enter()


class ProgressPage(BasePage):
    def __init__(self, state: dict):
        super().__init__(state)
        self.status = QLabel()
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        mono = QFont("Monospace")
        mono.setStyleHint(QFont.StyleHint.TypeWriter)
        self.log.setFont(mono)
        self.reboot_btn = QPushButton()
        self.reboot_btn.setObjectName("primary")
        self.reboot_btn.hide()
        self.reboot_btn.clicked.connect(
            lambda: QProcess.startDetached("systemctl", ["reboot"])
        )

        self.body.addWidget(self.status)
        self.body.addWidget(self.log, 1)
        self.body.addWidget(self.reboot_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.proc: QProcess | None = None
        self._logfile = None
        self.retranslate()

    def start_install(self, config_path: Path, creds_path: Path) -> None:
        self.status.setText(tr("progress_running"))
        Path("/tmp/pzhavos").mkdir(parents=True, exist_ok=True)
        self._logfile = open("/tmp/pzhavos/install.log", "a", encoding="utf-8")

        self.proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("TERM", "dumb")
        self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._append)
        self.proc.finished.connect(self._done)
        self.proc.start(
            "archinstall",
            ["--config", str(config_path), "--creds", str(creds_path), "--silent"],
        )

    def _append(self) -> None:
        text = bytes(self.proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        if self._logfile:
            self._logfile.write(text)
            self._logfile.flush()
        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(text)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _done(self, code: int, _status) -> None:
        if self._logfile:
            self._logfile.close()
            self._logfile = None
        ok = code == 0
        self.status.setText(tr("progress_done") if ok else tr("progress_fail"))
        self.reboot_btn.setVisible(ok)

    def retranslate(self) -> None:
        self.title.setText(tr("progress_title"))
        self.reboot_btn.setText(tr("reboot"))
