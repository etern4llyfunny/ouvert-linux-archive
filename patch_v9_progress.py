#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PzhavOS — патч v9: ИНДИКАТОР ХОДА УСТАНОВКИ.

ПРОБЛЕМА: установка идёт 10-30 минут, экран при этом почти неподвижен.
Пользователь не понимает, живо оно или повисло, и может нажать ребут
посреди pacstrap.

ЧТО ДОБАВЛЯЕТ (installer/pages.py, ProgressPage):
  1) Маркиз — бегущая полоса QProgressBar(range 0,0). Крутится, пока жив
     процесс archinstall. Отвечает на вопрос «оно вообще работает?».
  2) Строка текущего этапа под полосой. Парсится из потока archinstall:
        "Installing packages: ['plasma-meta']"  -> «Устанавливаю: plasma-meta»
        "Installing profile KDE Plasma..."      -> «Ставлю окружение: KDE Plasma»
        Fetching / device modifications / fstab / Syncing -> свои фразы
     Эти строки РЕАЛЬНО есть — сняты с лога t23 (27.07.2026).
  3) Счётчик пакетов «Пакеты: 347 из 932» — ТОЛЬКО если archinstall отдаст
     в stdout строки pacman вида "(347/932) installing foo".
     ЧЕСТНО: в /var/log/archinstall/install.log таких строк НЕТ (проверено
     grep'ом на t23, 0 совпадений). Возможно, в stdout они есть — лог и
     stdout у archinstall разные каналы. Код написан так, что если строки
     не придут, счётчик просто не появится, а маркиз и этапы работают.

ПОЧЕМУ ПОЛОСА ВСЕГДА МАРКИЗ, а не заполняется: pacman запускается ПАЧКАМИ
(base -> grub -> профиль DE -> наши пакеты). Заполняющаяся полоса дошла бы
до 100%, обнулилась и снова поползла — а на plasma-meta встала бы на две
минуты. Честная бегущая полоса врёт меньше.

  4) i18n.py: новые строки этапов + текст «обычно 10-30 минут» в статусе.

СВОЙСТВА: транзакционный, идемпотентный, компилирует результат до записи.

ЗАПУСК:  python3 patch_v9_progress.py [КОРЕНЬ_ПРОЕКТА]
"""

import sys
from pathlib import Path

# ─────────────────────────────── pages.py ───────────────────────────────

P_OLD_IMPORT = """    QButtonGroup, QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton, QRadioButton, QScrollArea,
    QVBoxLayout, QWidget,
)
"""

P_NEW_IMPORT = """    QButtonGroup, QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QProgressBar, QPushButton, QRadioButton,
    QScrollArea, QVBoxLayout, QWidget,
)
"""

P_OLD_ANSI = '_ANSI = re.compile(r"\\x1b\\[[0-9;]*m")\n'

P_NEW_ANSI = '''_ANSI = re.compile(r"\\x1b\\[[0-9;]*m")

# --- v9: разбор потока archinstall для индикатора этапа ---
# Префикс логгера "[2026-07-27 12:00:50] - INFO - ". В stdout обычно не
# приходит (в GUI строки видны голыми), но если придёт — срежем.
_RE_LOGPFX = re.compile(r"^\\[[^\\]]+\\]\\s*-\\s*\\w+\\s*-\\s*")
# pacman: "(347/932) installing foo". В /var/log/archinstall/install.log
# таких строк НЕТ (проверено на t23). Если не придут и в stdout — счётчик
# просто не появится, остальное работает.
_RE_PKGNUM = re.compile(r"\\((\\d+)/(\\d+)\\)\\s+\\w+")
# Эти две ТОЧНО есть, сняты с живого лога t23.
_RE_PKGS = re.compile(r"Installing packages:\\s*\\[(.+?)\\]")
_RE_PROFILE = re.compile(r"Installing profile\\s+(.+?)\\s*\\.{0,3}$")
# Общие фазы: подстрока -> ключ i18n.
_STAGE_HINTS = (
    ("fetching", "stage_db"),
    ("device modifications", "stage_disk"),
    ("fstab", "stage_fstab"),
    ("syncing", "stage_sync"),
)
'''

P_OLD_INIT = """        self.body.addWidget(self.status)
        self.body.addWidget(self.log, 1)
        self.body.addWidget(self.reboot_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.proc: QProcess | None = None
        self._logfile = None
        self.retranslate()
"""

P_NEW_INIT = '''        # --- v9: маркиз + строка этапа ---
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 0)          # 0,0 = бесконечная бегущая полоса
        self.bar.setFixedHeight(10)
        self.bar.setStyleSheet(
            "QProgressBar { background: #2b2b2b; border: none; border-radius: 5px; }"
            "QProgressBar::chunk { background: #4a9d94; border-radius: 5px; }"
        )
        self.stage = QLabel()
        self.stage.setStyleSheet("color: #9aa0a6;")
        self.bar.hide()
        self.stage.hide()

        self.body.addWidget(self.status)
        self.body.addWidget(self.bar)
        self.body.addWidget(self.stage)
        self.body.addWidget(self.log, 1)
        self.body.addWidget(self.reboot_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.proc: QProcess | None = None
        self._logfile = None
        self._buf = ""          # хвост неполной строки между чтениями
        self.retranslate()
'''

P_OLD_START = """    def start_install(self, config_path: Path, creds_path: Path) -> None:
        self.status.setText(tr("progress_running"))
"""

P_NEW_START = """    def start_install(self, config_path: Path, creds_path: Path) -> None:
        self.status.setText(tr("progress_running"))
        self._buf = ""
        self.bar.show()
        self.stage.setText(tr("stage_prepare"))
        self.stage.show()
"""

P_OLD_APPEND = """        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(text)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())
"""

P_NEW_APPEND = '''        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(text)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())
        self._scan(text)

    def _scan(self, chunk: str) -> None:
        """Вытаскивает из потока archinstall текущий этап. Никогда не кидает
        исключений наружу: сломанный индикатор не должен ронять установку."""
        try:
            self._buf += chunk
            parts = self._buf.split("\\n")
            self._buf = parts.pop()          # хвост без \\n оставляем на потом
            for raw in parts:
                line = _RE_LOGPFX.sub("", _ANSI.sub("", raw).strip())
                if not line:
                    continue

                m = _RE_PKGNUM.search(line)
                if m:
                    self.stage.setText(tr("stage_pkg") % (m.group(1), m.group(2)))
                    continue

                m = _RE_PROFILE.search(line)
                if m:
                    self.stage.setText(tr("stage_profile") % m.group(1))
                    continue

                m = _RE_PKGS.search(line)
                if m:
                    names = [n.strip().strip("'\\"") for n in m.group(1).split(",")]
                    names = [n for n in names if n]
                    shown = ", ".join(names[:3])
                    if len(names) > 3:
                        shown += " +%d" % (len(names) - 3)
                    self.stage.setText(tr("stage_pkgs") % shown)
                    continue

                low = line.lower()
                for needle, key in _STAGE_HINTS:
                    if needle in low:
                        self.stage.setText(tr(key))
                        break
        except Exception:
            pass
'''

P_OLD_DONE = """        ok = code == 0
        self.status.setText(tr("progress_done") if ok else tr("progress_fail"))
"""

P_NEW_DONE = """        ok = code == 0
        self.bar.hide()
        self.stage.hide()
        self.status.setText(tr("progress_done") if ok else tr("progress_fail"))
"""

# ─────────────────────────────── i18n.py ───────────────────────────────

I_OLD_RUNNING = (
    '    "progress_running": {"ru": "Идёт установка, не выключай компьютер…",'
    ' "en": "Installing, do not power off…"},\n'
)
I_NEW_RUNNING = (
    '    "progress_running": {"ru": "Идёт установка. Обычно занимает 10–30 минут — '
    'не выключай компьютер.", "en": "Installing. Usually takes 10–30 minutes — '
    'do not power off."},\n'
)

I_OLD_REBOOT = '    "reboot": {"ru": "Перезагрузить", "en": "Reboot"},\n}\n'

I_NEW_REBOOT = '''    "reboot": {"ru": "Перезагрузить", "en": "Reboot"},

    # --- v9: индикатор этапа установки ---
    "stage_prepare": {"ru": "Подготовка…", "en": "Preparing…"},
    "stage_db": {"ru": "Обновляю базу пакетов…", "en": "Refreshing package database…"},
    "stage_disk": {"ru": "Размечаю диск…", "en": "Partitioning the disk…"},
    "stage_pkgs": {"ru": "Устанавливаю: %s", "en": "Installing: %s"},
    "stage_profile": {"ru": "Ставлю окружение: %s", "en": "Installing desktop: %s"},
    "stage_pkg": {"ru": "Пакеты: %s из %s", "en": "Packages: %s of %s"},
    "stage_fstab": {"ru": "Записываю таблицу разделов…", "en": "Writing fstab…"},
    "stage_sync": {"ru": "Сбрасываю данные на диск…", "en": "Syncing to disk…"},
}
'''

EDITS = {
    "installer/pages.py": [
        ("импорт QProgressBar", P_OLD_IMPORT, P_NEW_IMPORT),
        ("регексы разбора потока", P_OLD_ANSI, P_NEW_ANSI),
        ("виджеты маркиза в __init__", P_OLD_INIT, P_NEW_INIT),
        ("показ маркиза в start_install", P_OLD_START, P_NEW_START),
        ("разбор потока в _append + _scan", P_OLD_APPEND, P_NEW_APPEND),
        ("скрытие маркиза в _done", P_OLD_DONE, P_NEW_DONE),
    ],
    "installer/i18n.py": [
        ("текст статуса с оценкой времени", I_OLD_RUNNING, I_NEW_RUNNING),
        ("строки этапов", I_OLD_REBOOT, I_NEW_REBOOT),
    ],
}


def find_root(argv):
    if len(argv) > 1:
        return Path(argv[1]).expanduser().resolve()
    for cand in (Path.cwd(), Path.cwd() / "pzhavos", Path.home() / "pzhavos"):
        if (cand / "installer" / "pages.py").is_file():
            return cand.resolve()
    return None


def main():
    root = find_root(sys.argv)
    if root is None or not (root / "installer" / "pages.py").is_file():
        print("ОШИБКА: не найден installer/pages.py.")
        print("Запусти:  python3 patch_v9_progress.py /путь/к/pzhavos")
        return 1

    print(f"Корень проекта: {root}")
    print("─" * 70)

    planned = {}
    skipped = 0
    problems = []

    for rel, edits in EDITS.items():
        path = root / rel
        if not path.is_file():
            problems.append(f"{rel}: ФАЙЛ НЕ НАЙДЕН")
            continue
        text = path.read_text(encoding="utf-8")
        orig = text
        for name, old, new in edits:
            if new in text:
                print(f"  = {rel}: «{name}» уже применён")
                skipped += 1
                continue
            n = text.count(old)
            if n != 1:
                problems.append(
                    f"{rel}: якорь «{name}» найден {n} раз (нужно ровно 1)")
                continue
            text = text.replace(old, new, 1)
            print(f"  + {rel}: «{name}» — применяю")
        if text != orig:
            try:
                compile(text, str(path), "exec")
            except SyntaxError as e:
                problems.append(f"{rel}: результат НЕ КОМПИЛИРУЕТСЯ: {e}")
                continue
            planned[path] = text

    print("─" * 70)
    if problems:
        print("ОТКАТ. Ни один файл НЕ изменён. Причины:")
        for p in problems:
            print(f"  ! {p}")
        return 2

    if not planned:
        print(f"Изменений нет — всё уже на месте ({skipped} пунктов). OK.")
        return 0

    for path, text in planned.items():
        bak = path.with_suffix(path.suffix + ".v9bak")
        if not bak.exists():
            bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.write_text(text, encoding="utf-8")
        print(f"  ЗАПИСАН: {path}  (бэкап: {bak.name})")

    print("─" * 70)
    print("ГОТОВО. Бэкапы .v9bak убери из installer/ перед сборкой ISO!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
