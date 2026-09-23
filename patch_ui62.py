#!/usr/bin/env python3
"""Патч 62: окно без кнопок + защита от закрытия, хвосты старой палитры,
base-devel, обои KDE.

Правит ОБЕ копии установщика:
  ~/pzhavos/installer/
  ~/pzhavos/iso/profile/airootfs/opt/ouvert-installer/

  wizard.py   Frameless (кнопок нет физически) + closeEvent:
              идёт установка -> отказ; до установки -> «Выйти?» (по умолч. Отмена);
              после установки -> закрывается молча.
  main.py     --smoke-test: app.quit -> app.exit. В Qt 6 quit() шлёт окнам
              close, closeEvent спросил бы «Выйти?» и тест повис бы.
  i18n.py     close_ask / close_yes / close_busy.
  pages.py    цвета берутся из theme.C вместо старой палитры PzhavOS:
              статус сети, подписи сводки (Bug 59), прогресс-бар (Bug 60),
              строка этапа.
  config_gen  + base-devel (Bug 61: без него paru не собирает AUR);
              KDE копировал ouvert-kde.png, выброшенный Патчем 60 (Bug 58).

Идемпотентен. Бэкап: <файл>.p62bak-<YYYYMMDD-HHMMSS>
Размеры печатаются в БАЙТАХ (урок Патча 61).
"""

import os
import shutil
import sys
from datetime import datetime

ROOTS = [
    os.path.expanduser("~/pzhavos/installer"),
    os.path.expanduser("~/pzhavos/iso/profile/airootfs/opt/ouvert-installer"),
]

# --- pages.py -----------------------------------------------------------

P_IMPORT_OLD = "from i18n import current_lang, set_lang, tr\n"
P_IMPORT_NEW = "from i18n import current_lang, set_lang, tr\nfrom theme import C\n"

P_STATUS_OLD = '        color = {True: "#5fd3c8", False: "#c67573", None: "#a0a0a0"}[ok]\n'
P_STATUS_NEW = '        color = {True: C["blue"], False: C["coral"], None: C["muted"]}[ok]\n'

P_SUMMARY_OLD = (
    "            f\"<p style='margin:6px 0'><span style='color:#c67573'>{k}:</span> {v}</p>\"\n"
)
P_SUMMARY_NEW = (
    "            f\"<p style='margin:6px 0'><span style='color:{C['muted']}'>{k}:</span> {v}</p>\"\n"
)

P_BAR_OLD = (
    "        self.bar.setStyleSheet(\n"
    "            \"QProgressBar { background: #2b2b2b; border: none; border-radius: 5px; }\"\n"
    "            \"QProgressBar::chunk { background: #4a9d94; border-radius: 5px; }\"\n"
    "        )\n"
)
# Геометрию (без рамки, радиус 5 при высоте 10) оставляем проверенную,
# меняем только цвета. Глобальное правило темы рассчитано на радиус 6
# и рамку 1px — на полоске высотой 10 это не проверялось.
P_BAR_NEW = (
    "        self.bar.setStyleSheet(\n"
    "            f\"QProgressBar {{ background: {C['line']}; border: none; border-radius: 5px; }}\"\n"
    "            f\"QProgressBar::chunk {{ background: {C['blue']}; border-radius: 5px; }}\"\n"
    "        )\n"
)

P_STAGE_OLD = '        self.stage.setStyleSheet("color: #9aa0a6;")\n'
P_STAGE_NEW = '        self.stage.setObjectName("muted")\n'

# --- wizard.py ----------------------------------------------------------

W_IMPORT_OLD = "from PySide6.QtCore import Qt\n"
W_IMPORT_NEW = "from PySide6.QtCore import QProcess, Qt\n"

W_FRAME_OLD = (
    "    def __init__(self):\n"
    "        super().__init__()\n"
    "        self.state: dict = {\n"
)
W_FRAME_NEW = (
    "    def __init__(self):\n"
    "        super().__init__()\n"
    "        # Патч 62: без рамки — кнопок свернуть/развернуть/закрыть нет\n"
    "        # физически. В COSMIC (Wayland) декорации рисует композитор, и\n"
    "        # убрать ОДНУ кнопку протокол не позволяет — только всю рамку.\n"
    "        # Alt+F4 рамку не спрашивает, его ловит closeEvent ниже.\n"
    "        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)\n"
    "        self.state: dict = {\n"
)

W_CLOSE_OLD = (
    "    def retranslate_all(self) -> None:\n"
    "        self.setWindowTitle(tr(\"app_title\"))\n"
    "        self.header_title.setText(tr(\"app_title\"))\n"
    "        for p in self.pages:\n"
    "            p.retranslate()\n"
    "        self.update_nav()\n"
)
W_CLOSE_NEW = W_CLOSE_OLD + (
    "\n"
    "    def closeEvent(self, event) -> None:\n"
    "        \"\"\"Патч 62. Кнопок у окна нет, но Alt+F4 и «Закрыть» из панели\n"
    "        задач всё равно присылают запрос на закрытие.\"\"\"\n"
    "        proc = self.progress.proc\n"
    "        if proc is not None and proc.state() != QProcess.ProcessState.NotRunning:\n"
    "            # оборванный archinstall оставляет диск полуразмеченным\n"
    "            QMessageBox.warning(self, \"Ouvert Linux\", tr(\"close_busy\"))\n"
    "            event.ignore()\n"
    "            return\n"
    "        if self.stack.currentIndex() == self.progress_index:\n"
    "            event.accept()  # установка закончилась — держать незачем\n"
    "            return\n"
    "        box = QMessageBox(QMessageBox.Icon.Question, \"Ouvert Linux\",\n"
    "                          tr(\"close_ask\"), parent=self)\n"
    "        yes = box.addButton(tr(\"close_yes\"), QMessageBox.ButtonRole.AcceptRole)\n"
    "        box.setDefaultButton(\n"
    "            box.addButton(tr(\"pe_cancel\"), QMessageBox.ButtonRole.RejectRole)\n"
    "        )\n"
    "        box.exec()\n"
    "        if box.clickedButton() is not yes:\n"
    "            event.ignore()\n"
)

# Патч 62б: диалог «Выйти?» тоже без рамки. С рамкой у него было
# «развернуть» — и окно-вопрос раскрывалось на весь экран ради одной
# строчки. Флаги «только заголовок + крестик» Qt-декорация проигнорировала
# (проверено на niri 22.09.26: кнопки остались), а Frameless — выполняет.
# Край окна рисует композитор: фокусная обводка есть и в niri, и в COSMIC.
W_DLG_OLD = "        yes = box.addButton(tr(\"close_yes\"), QMessageBox.ButtonRole.AcceptRole)\n"
W_DLG_NEW = (
    "        box.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)\n"
) + W_DLG_OLD

# Первая версия 62б (флаги, не сработали) — убрать, если уже применена.
W_FLAGS_OLD = (
    "        box.setWindowFlags(\n"
    "            Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint\n"
    "            | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint\n"
    "        )\n"
)

# --- main.py ------------------------------------------------------------

M_SMOKE_OLD = "        QTimer.singleShot(300, app.quit)\n"
M_SMOKE_NEW = (
    "        # exit, а не quit: в Qt 6 quit() шлёт окнам close, а closeEvent\n"
    "        # спрашивает «Выйти?» — смоук-тест повис бы на диалоге (Патч 62).\n"
    "        QTimer.singleShot(300, app.exit)\n"
)

# --- i18n.py ------------------------------------------------------------

I_OLD = '    "step": {"ru": "Шаг", "en": "Step"},\n'
I_NEW = I_OLD + (
    "\n"
    "    # --- Патч 62: закрытие окна ---\n"
    '    "close_ask": {"ru": "Выйти из установщика? Система не будет установлена.",\n'
    '                  "en": "Quit the installer? The system will not be installed."},\n'
    '    "close_yes": {"ru": "Выйти", "en": "Quit"},\n'
    '    "close_busy": {\n'
    '        "ru": "Идёт установка — закрыть установщик сейчас нельзя.\\n"\n'
    '              "Прерванная установка оставит диск наполовину размеченным.",\n'
    '        "en": "Installation is running — the installer cannot be closed now.\\n"\n'
    '              "An interrupted install leaves the disk half-partitioned.",\n'
    "    },\n"
)

# --- config_gen.py ------------------------------------------------------

C_PKG_OLD = '    "git",\n'
C_PKG_NEW = (
    '    "git",\n'
    '    "base-devel",  # Bug 61: без него paru не собирает AUR (нет fakeroot)\n'
)

C_KDE_OLD = "/usr/share/wallpapers/Ouvert/ouvert-kde.png"
C_KDE_NEW = "/usr/share/wallpapers/Ouvert/ouvert.png"

C_KDECOM_OLD = "        # KDE Plasma: свои обои ouvert-kde.png. Дефолт в Plasma без правки\n"
C_KDECOM_NEW = (
    "        # KDE Plasma: те же ouvert.png (отдельные KDE-обои выброшены Патчем 60,\n"
    "        # Bug 58: cp молча падал на || true). Дефолт в Plasma без правки\n"
)

EDITS = {
    "pages.py": [
        (P_IMPORT_OLD, P_IMPORT_NEW),
        (P_STATUS_OLD, P_STATUS_NEW),
        (P_SUMMARY_OLD, P_SUMMARY_NEW),
        (P_BAR_OLD, P_BAR_NEW),
        (P_STAGE_OLD, P_STAGE_NEW),
    ],
    "wizard.py": [
        (W_IMPORT_OLD, W_IMPORT_NEW),
        (W_FRAME_OLD, W_FRAME_NEW),
        # Третий элемент — маркер «уже сделано». Нужен, потому что W_DLG
        # правит текст ВНУТРИ вставки W_CLOSE: без маркера W_CLOSE перестаёт
        # узнавать себя и вставляет второй closeEvent.
        (W_CLOSE_OLD, W_CLOSE_NEW, "    def closeEvent("),
        (W_FLAGS_OLD, ""),  # нет блока -> пропуск; есть -> удалить
        (W_DLG_OLD, W_DLG_NEW, "box.setWindowFlag(Qt.WindowType.FramelessWindowHint"),  # строго ПОСЛЕ W_CLOSE
    ],
    "main.py": [
        (M_SMOKE_OLD, M_SMOKE_NEW),
    ],
    "i18n.py": [
        (I_OLD, I_NEW),
    ],
    "config_gen.py": [
        (C_PKG_OLD, C_PKG_NEW),
        (C_KDECOM_OLD, C_KDECOM_NEW),
        (C_KDE_OLD, C_KDE_NEW),
    ],
}

# После патча этих строк не должно остаться нигде
FORBIDDEN = {
    "pages.py": ["#5fd3c8", "#c67573", "#a0a0a0", "#4a9d94", "#2b2b2b", "#9aa0a6"],
    "config_gen.py": ["ouvert-kde.png"],
    "main.py": ["app.quit"],
    "wizard.py": ["WindowCloseButtonHint"],
}


def plan_file(path: str, edits: list) -> tuple[str, str, int]:
    """Считает новый текст В ПАМЯТИ и проверяет его. На диск не пишет."""
    if not os.path.isfile(path):
        sys.exit(f"НЕТ ФАЙЛА: {path}")
    text = open(path, encoding="utf-8").read()
    new = text
    applied = 0
    for old, repl, *marker in edits:
        n = new.count(old)
        if marker:
            if marker[0] in new:
                continue
        elif old in repl:
            # вставка: old остаётся внутри repl, «применено» = repl уже есть
            if repl in new:
                continue
        elif n == 0 and repl in new:
            # замена: old исчез, repl на месте. Смотреть только на repl
            # нельзя — короткий repl может жить в файле и так (Bug 58:
            # путь ouvert.png уже есть в блоке XFCE).
            continue
        if n != 1:
            sys.exit(f"СТОП: в {path} ожидалось 1 вхождение, найдено {n}:\n{old[:120]!r}")
        new = new.replace(old, repl)
        applied += 1

    for bad in FORBIDDEN.get(os.path.basename(path), []):
        if bad in new:
            sys.exit(f"СТОП: в {path} осталось {bad!r}")
    compile(new, path, "exec")
    return text, new, applied


def main() -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Проход 1: всё считаем и проверяем. Любой СТОП — ни один файл не тронут.
    plans = []
    for root in ROOTS:
        for name, edits in EDITS.items():
            path = os.path.join(root, name)
            plans.append((path, *plan_file(path, edits)))

    # Проход 2: пишем.
    for path, text, new, applied in plans:
        if applied == 0:
            print(f"уже пропатчен: {path}")
            continue
        shutil.copy2(path, f"{path}.p62bak-{stamp}")
        open(path, "w", encoding="utf-8").write(new)
        b0, b1 = len(text.encode()), len(new.encode())
        print(f"OK  {path}  ({applied} правок, {b0} -> {b1} байт)")

    print()
    ok = True
    for name in EDITS:
        a, b = (open(os.path.join(r, name), "rb").read() for r in ROOTS)
        same = a == b
        ok &= same
        print(f"{name:15} {len(a):>6} байт  {'копии совпадают' if same else 'КОПИИ РАЗОШЛИСЬ'}")
    if not ok:
        sys.exit("\nВНИМАНИЕ: копии разошлись — разбираться до сборки ISO")


if __name__ == "__main__":
    main()
