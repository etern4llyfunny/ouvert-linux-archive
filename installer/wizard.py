"""Главное окно установщика: шапка, стек страниц, навигация, запуск установки."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from config_gen import write_configs
from i18n import tr
from pages import (
    DesktopPage, DiskPage, GfxPage, NetworkPage, ProgressPage, ReposPage,
    SummaryPage, TimezonePage, UserPage, WelcomePage,
)

ASSETS = Path(__file__).resolve().parent / "assets"
LIVE_MARKER = Path("/run/archiso")


class InstallerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state: dict = {
            "lang": "ru",
            "username": "",
            "password": "",
            "password2": "",
            "hostname": "pzhavos",
            "profile": "KDE Plasma",
            "profile_name": "KDE Plasma",
            "greeter": "plasma-login-manager",
            "disk": None,
            "disk_desc": None,
            "disk_size": 0,
            "net_ok": False,
            "timezone": "Europe/Moscow",
            "gfx": "All open-source",
            "repos": ["multilib"],
        }

        # --- шапка ---
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(64)
        h = QHBoxLayout(header)
        h.setContentsMargins(20, 8, 20, 8)

        logo = QLabel()
        logo_path = ASSETS / "logo.png"
        if logo_path.exists():
            logo.setPixmap(
                QPixmap(str(logo_path)).scaled(
                    44, 44,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        self.header_title = QLabel()
        self.header_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.step_label = QLabel()
        self.step_label.setObjectName("stepLabel")

        h.addWidget(logo)
        h.addSpacing(10)
        h.addWidget(self.header_title)
        h.addStretch()
        h.addWidget(self.step_label)

        # --- страницы ---
        welcome = WelcomePage(self.state)
        welcome.lang_changed.connect(self.retranslate_all)
        self.progress = ProgressPage(self.state)
        self.net_page = NetworkPage(self.state)
        self.pages = [
            welcome,
            self.net_page,
            TimezonePage(self.state),
            DiskPage(self.state),
            UserPage(self.state),
            DesktopPage(self.state),
            GfxPage(self.state),
            ReposPage(self.state),
            SummaryPage(self.state),
            self.progress,
        ]
        self.summary_index = len(self.pages) - 2
        self.progress_index = len(self.pages) - 1

        self.stack = QStackedWidget()
        for p in self.pages:
            self.stack.addWidget(p)

        # --- навигация ---
        nav = QHBoxLayout()
        nav.setContentsMargins(36, 12, 36, 20)
        self.btn_back = QPushButton()
        self.btn_next = QPushButton()
        self.btn_next.setObjectName("primary")
        self.btn_back.clicked.connect(lambda: self.go(-1))
        self.btn_next.clicked.connect(lambda: self.go(+1))
        nav.addWidget(self.btn_back)
        nav.addStretch()
        nav.addWidget(self.btn_next)

        root = QWidget()
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(header)
        v.addWidget(self.stack, 1)
        v.addLayout(nav)
        self.setCentralWidget(root)

        self.retranslate_all()

    # --- логика ---
    def _validate(self) -> str | None:
        s = self.state
        if not s.get("disk"):
            return tr("err_no_disk")
        if not s.get("username") or not s.get("password"):
            return tr("err_user")
        if s.get("password") != s.get("password2"):
            return tr("err_pass")
        return None

    def _start_install(self) -> None:
        err = self._validate()
        if err:
            QMessageBox.warning(self, "PzhavOS", err)
            return
        cfg, creds = write_configs(self.state)
        if not LIVE_MARKER.exists():
            QMessageBox.information(self, "PzhavOS", tr("not_live"))
            return
        self.btn_back.hide()
        self.btn_next.hide()
        self.stack.setCurrentIndex(self.progress_index)
        self.update_nav()
        self.progress.start_install(cfg, creds)

    def go(self, delta: int) -> None:
        i = self.stack.currentIndex()
        if i == self.progress_index:
            return
        if delta > 0 and self.pages[i] is self.net_page and not self.state.get("net_ok"):
            QMessageBox.warning(self, "PzhavOS", tr("err_no_net"))
            return
        if delta > 0 and i == self.summary_index:
            self._start_install()
            return
        i = max(0, min(len(self.pages) - 1, i + delta))
        self.stack.setCurrentIndex(i)
        self.pages[i].on_enter()
        self.update_nav()

    def update_nav(self) -> None:
        i = self.stack.currentIndex()
        self.btn_back.setEnabled(i > 0)
        self.btn_next.setText(tr("install") if i == self.summary_index else tr("next"))
        self.btn_back.setText(tr("back"))
        self.step_label.setText(f"{tr('step')} {i + 1} / {len(self.pages)}")

    def retranslate_all(self) -> None:
        self.setWindowTitle(tr("app_title"))
        self.header_title.setText(tr("app_title"))
        for p in self.pages:
            p.retranslate()
        self.update_nav()
