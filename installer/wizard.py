"""Главное окно установщика: шапка, стек страниц, кнопки Назад/Далее."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from i18n import tr
from pages import DesktopPage, StubPage, SummaryPage, UserPage, WelcomePage

ASSETS = Path(__file__).resolve().parent / "assets"


class InstallerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state: dict = {
            "lang": "ru",
            "username": "",
            "password": "",
            "hostname": "pzhavos",
            "profile": "plasma",
            "profile_name": "KDE Plasma",
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
        self.pages = [
            welcome,
            StubPage(self.state, "network_title", "network_stub"),
            StubPage(self.state, "disk_title", "disk_stub"),
            UserPage(self.state),
            DesktopPage(self.state),
            SummaryPage(self.state),
        ]
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
    def go(self, delta: int) -> None:
        i = self.stack.currentIndex()
        if delta > 0 and i == len(self.pages) - 1:
            QMessageBox.information(self, "PzhavOS", tr("install_stub"))
            return
        i = max(0, min(len(self.pages) - 1, i + delta))
        self.stack.setCurrentIndex(i)
        self.pages[i].on_enter()
        self.update_nav()

    def update_nav(self) -> None:
        i = self.stack.currentIndex()
        last = i == len(self.pages) - 1
        self.btn_back.setEnabled(i > 0)
        self.btn_next.setText(tr("install") if last else tr("next"))
        self.btn_back.setText(tr("back"))
        self.step_label.setText(f"{tr('step')} {i + 1} / {len(self.pages)}")

    def retranslate_all(self) -> None:
        self.setWindowTitle(tr("app_title"))
        self.header_title.setText(tr("app_title"))
        for p in self.pages:
            p.retranslate()
        self.update_nav()
