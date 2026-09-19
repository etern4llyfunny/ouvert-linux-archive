"""Главное окно установщика: шапка, стек страниц, навигация, запуск установки.

ВЕРСИЯ: v4 — добавлена страница «Разметка» (11 страниц).
"""
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
    DesktopPage, DiskPage, GfxPage, NetworkPage, ProgressPage,
    SummaryPage, UserPage, WelcomePage,
)
from partitioning import PartitioningPage
from system import AdvancedPage, RegionPage

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
            "hostname": "ouvert",
            "profile": "Cinnamon",
            "profile_name": "Cinnamon",
            "greeter": "lightdm-gtk-greeter",
            "disk": None,
            "disk_desc": None,
            "disk_size": 0,
            "net_ok": False,
            "timezone": "Europe/Moscow",
            "gfx": "All open-source",
            "repos": ["multilib"],
            "kb": "us_ru",
            "kernel": "linux",
            # --- v4: разметка ---
            "part_mode": "wipe",       # wipe | manual
            "part_desc": "",
            "fs": "ext4",
            "btrfs_subvols": True,
            "btrfs_compress": True,
            "separate_home": False,
            "root_size_gib": 40,
            "luks": False,
            "luks_password": "",
            "luks_password2": "",
            "manual_parts": [],
            "sector_size": 512,
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
            RegionPage(self.state),
            DiskPage(self.state),
            PartitioningPage(self.state),
            UserPage(self.state),
            DesktopPage(self.state),
            GfxPage(self.state),
            AdvancedPage(self.state),
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
    def _validate_disk(self) -> str | None:
        """Гейт страницы «Диск»: без диска дальше не пускаем."""
        if not self.state.get("disk"):
            return tr("err_no_disk")
        return None

    def _validate_part(self) -> str | None:
        """Гейт страницы «Разметка»."""
        s = self.state

        if s.get("part_mode") == "manual":
            mps = [p.get("mountpoint") for p in s.get("manual_parts") or [] if p.get("mountpoint")]
            if "/" not in mps:
                return tr("err_no_root")
            # boot_partition ищется по флагу boot + точке монтирования;
            # без него archinstall не поставит GRUB ни в UEFI, ни в BIOS
            if "/boot" not in mps:
                return tr("err_no_boot")
            if len(mps) != len(set(mps)):
                return tr("err_dup_mount")
            from diskmap import LINUX_FS, is_fat
            for p in s.get("manual_parts") or []:
                mp = p.get("mountpoint")
                if not mp:
                    continue
                # ЭФФЕКТИВНАЯ ФС — та, что окажется на разделе ПОСЛЕ
                # установки. Проверять только «сохраняем» мало: ntfs
                # можно выбрать и в списке при форматировании.
                if p.get("format"):
                    fs = (p.get("fs") or "").lower()
                else:
                    fs = (p.get("cur_fs") or "").lower()
                    if not fs:
                        return tr("err_no_fs") % (p["path"], mp)
                if mp == "/" and fs not in LINUX_FS:
                    return tr("err_root_fs") % fs
                # /boot бывает и fat32 (когда ESP смонтирован как /boot),
                # и ext4 (когда ESP вынесен отдельно в /efi) — годятся оба
                if mp == "/boot" and fs not in LINUX_FS and not is_fat(fs):
                    return tr("err_boot_fs") % fs
                if mp == "/efi" and not is_fat(fs):
                    return tr("err_efi_fs") % fs
            return None

        # режим «Стереть диск»
        from config_gen import ROOT_START_MIB, available_mib, use_separate_home

        avail = available_mib(s)
        if avail - ROOT_START_MIB < 8 * 1024:
            return tr("err_disk_small")
        if use_separate_home(s):
            root_mib = int(s.get("root_size_gib") or 0) * 1024
            if avail - ROOT_START_MIB - root_mib < 8 * 1024:
                return tr("err_root_size")
        if s.get("luks"):
            if not s.get("luks_password"):
                return tr("err_luks_empty")
            if s.get("luks_password") != s.get("luks_password2"):
                return tr("err_luks_pass")
        return None

    def _validate(self) -> str | None:
        s = self.state
        if not s.get("disk"):
            return tr("err_no_disk")
        err = self._validate_part()
        if err:
            return err
        if not s.get("username") or not s.get("password"):
            return tr("err_user")
        if s.get("password") != s.get("password2"):
            return tr("err_pass")
        return None

    def _start_install(self) -> None:
        err = self._validate()
        if err:
            QMessageBox.warning(self, "Ouvert Linux", err)
            return
        cfg, creds = write_configs(self.state)
        if not LIVE_MARKER.exists():
            QMessageBox.information(self, "Ouvert Linux", tr("not_live"))
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

        if delta > 0:
            page = self.pages[i]
            if (check := getattr(page, "validate", None)) and (err := check()):
                QMessageBox.warning(self, "Ouvert Linux", err)
                return
            if page is self.net_page and not self.state.get("net_ok"):
                QMessageBox.warning(self, "Ouvert Linux", tr("err_no_net"))
                return
            if isinstance(page, DiskPage) and (err := self._validate_disk()):
                QMessageBox.warning(self, "Ouvert Linux", err)
                return
            if isinstance(page, PartitioningPage) and (err := self._validate_part()):
                QMessageBox.warning(self, "Ouvert Linux", err)
                return
            if i == self.summary_index:
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
