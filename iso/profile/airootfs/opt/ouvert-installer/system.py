"""Раскладка клавиатуры и выбор ядра.

Обе страницы — наследники существующих из pages.py, чтобы не трогать
проверенный файл и не плодить лишние шаги мастера:
  RegionPage   = TimezonePage  + раскладка
  AdvancedPage = ReposPage     + ядро
Страниц по-прежнему 11.

ОСТОРОЖНО: базовый __init__ вызывает retranslate() ДО того, как появятся
наши виджеты — все переопределения защищены hasattr.
"""
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel

from config_gen import KB_LAYOUTS, KERNEL_SETS, pick_console_font
from i18n import tr
from pages import ReposPage, TimezonePage

# ключ state -> ключ i18n
KB_CHOICES = ["us_ru", "us", "ru"]
KB_KEYS = {"us_ru": "kb_us_ru", "us": "kb_us", "ru": "kb_ru"}

KERNEL_CHOICES = ["ouvert", "ouvert+lts", "linux", "linux-lts"]
KERNEL_KEYS = {
    "ouvert": "kern_ouvert",
    "ouvert+lts": "kern_both",
    "linux": "kern_linux",
    "linux-lts": "kern_lts",
}


class RegionPage(TimezonePage):
    def __init__(self, state: dict):
        super().__init__(state)
        state.setdefault("kb", "us_ru" if state.get("lang") == "ru" else "us")

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        self.l_kb = QLabel()
        self.kb_combo = QComboBox()
        self.kb_combo.setFixedWidth(280)
        for key in KB_CHOICES:
            self.kb_combo.addItem(key, key)
        self.kb_combo.currentIndexChanged.connect(self._store_kb)

        self.kb_note = QLabel()
        self.kb_note.setObjectName("muted")
        self.kb_note.setWordWrap(True)

        form.addRow(self.l_kb, self.kb_combo)
        form.addRow(QLabel(), self.kb_note)
        self.body.addSpacing(10)
        self.body.addLayout(form)

        idx = self.kb_combo.findData(state["kb"])
        if idx >= 0:
            self.kb_combo.setCurrentIndex(idx)
        self.retranslate()

    def _store_kb(self) -> None:
        data = self.kb_combo.currentData()
        if data:
            self.state["kb"] = data
        self.retranslate()

    def retranslate(self) -> None:
        super().retranslate()
        if not hasattr(self, "kb_combo"):
            return  # вызов из TimezonePage.__init__, виджетов ещё нет
        self.title.setText(tr("region_title"))
        self.l_kb.setText(tr("kb_label"))
        cur = self.kb_combo.currentData()
        for i, key in enumerate(KB_CHOICES):
            self.kb_combo.setItemText(i, tr(KB_KEYS[key]))
        # Шрифт консоли выбирается сам по языку — показываем, что получилось
        font = pick_console_font(self.state.get("lang") or "en")
        note = tr("kb_note_us_ru") if cur == "us_ru" else tr("kb_note_single")
        self.kb_note.setText(f'{note}\n{tr("kb_console")}: {KB_LAYOUTS[cur or "us"]["kb_layout"]} / {font}')
        self.state["kb_desc"] = tr(KB_KEYS[cur or "us"])


class AdvancedPage(ReposPage):
    def __init__(self, state: dict):
        super().__init__(state)
        state.setdefault("kernel", "ouvert")

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        self.l_kern = QLabel()
        self.kern_combo = QComboBox()
        self.kern_combo.setFixedWidth(320)
        for key in KERNEL_CHOICES:
            self.kern_combo.addItem(key, key)
        self.kern_combo.currentIndexChanged.connect(self._store_kern)

        self.kern_note = QLabel()
        self.kern_note.setObjectName("muted")
        self.kern_note.setWordWrap(True)

        form.addRow(self.l_kern, self.kern_combo)
        form.addRow(QLabel(), self.kern_note)
        self.body.addSpacing(16)
        self.body.addLayout(form)

        idx = self.kern_combo.findData(state["kernel"])
        if idx >= 0:
            self.kern_combo.setCurrentIndex(idx)
        self.retranslate()

    def _store_kern(self) -> None:
        data = self.kern_combo.currentData()
        if data:
            self.state["kernel"] = data
        self.retranslate()

    def retranslate(self) -> None:
        super().retranslate()
        if not hasattr(self, "kern_combo"):
            return
        self.title.setText(tr("adv_title"))
        self.l_kern.setText(tr("kern_label"))
        for i, key in enumerate(KERNEL_CHOICES):
            self.kern_combo.setItemText(i, tr(KERNEL_KEYS[key]))
        pkgs = " + ".join(KERNEL_SETS.get(self.state.get("kernel") or "ouvert", ["linux-ouvert"]))
        self.kern_note.setText(f'{tr("kern_note")}\n{tr("kern_pkgs")}: {pkgs}')
        self.state["kernel_desc"] = pkgs
