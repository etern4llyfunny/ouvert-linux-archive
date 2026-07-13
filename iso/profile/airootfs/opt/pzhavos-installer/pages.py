"""Страницы установщика."""
import json
import subprocess
from pathlib import Path

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QRadioButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from desktops import DESKTOP_ENVIRONMENTS, WINDOW_MANAGERS
from i18n import set_lang, tr


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


class StubPage(BasePage):
    def __init__(self, state: dict, title_key: str, text_key: str):
        super().__init__(state)
        self.title_key = title_key
        self.text_key = text_key
        self.text = QLabel()
        self.text.setObjectName("muted")
        self.text.setWordWrap(True)
        self.notice = QLabel()
        self.notice.setObjectName("muted")
        self.body.addWidget(self.text)
        self.body.addSpacing(8)
        self.body.addWidget(self.notice)
        self.retranslate()

    def retranslate(self) -> None:
        self.title.setText(tr(self.title_key))
        self.text.setText(tr(self.text_key))
        self.notice.setText("⚠ " + tr("stub_notice"))


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
            (tr("desktop_label"), s.get("profile_name") or ns),
            (tr("disk_label"), s.get("disk_desc") or ns),
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
