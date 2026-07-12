"""Страницы установщика."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QRadioButton, QScrollArea, QVBoxLayout, QWidget,
)

from desktops import DESKTOP_ENVIRONMENTS, WINDOW_MANAGERS
from i18n import set_lang, tr


class BasePage(QWidget):
    """Базовая страница: заголовок + контент."""

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

    def retranslate(self) -> None:  # переопределяется в наследниках
        pass

    def on_enter(self) -> None:  # вызывается при показе страницы
        pass


class StubPage(BasePage):
    """Заглушка для страниц, которые пишем в следующих сессиях."""

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

        self.username.textChanged.connect(lambda t: self.state.update(username=t))
        self.password.textChanged.connect(lambda t: self.state.update(password=t))
        self.hostname.textChanged.connect(lambda t: self.state.update(hostname=t))

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

    def _fill(self, box: QGroupBox, items: list[tuple[str, str]]) -> None:
        lay = QVBoxLayout(box)
        for display, profile in items:
            rb = QRadioButton(display)
            rb.toggled.connect(
                lambda on, d=display, p=profile: on and self.state.update(
                    profile=p, profile_name=d
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
        ]
        html = "".join(
            f"<p style='margin:6px 0'><span style='color:#c67573'>{k}:</span> {v}</p>"
            for k, v in rows
        )
        self.text.setText(html)

    def retranslate(self) -> None:
        self.title.setText(tr("summary_title"))
        self.on_enter()
