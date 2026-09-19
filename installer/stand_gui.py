#!/usr/bin/env python3
"""
stand_gui.py — открыть ТОЛЬКО диалог «Разделы диска» на указанном устройстве.
Этап 5, сессия 4. Отладка записи БЕЗ ВМ.

ЗАЧЕМ: partops.write_allowed() требует root и /run/archiso. Второе снимается
белым списком OUVERT_PARTOPS_ALLOW, первое — нет. Значит проверить живые
кнопки можно либо в ВМ (медленно), либо здесь: настоящий loop-диск,
настоящий parted, настоящий mkfs, ноль риска для реальных дисков.

ЗАПУСК (fish, ОДНОЙ строкой):
  cd ~/ouvert/installer
  sudo -E env OUVERT_PARTOPS_ALLOW=/dev/loop0 python stand_gui.py /dev/loop0

ПРЕДОХРАНИТЕЛИ:
  • устройство обязано быть в OUVERT_PARTOPS_ALLOW — иначе выход
  • OUVERT_DISKMAP_SAMPLE запрещён: стенд чтения и стенд записи вместе
    дают картинку из файла и запись в реальный диск. Это худший из миров.
  • отказ, если имя не начинается с /dev/loop — руками поменяешь строку
    ниже, если однажды понадобится настоящий диск в ВМ.
"""

import os
import sys

ALLOW_PREFIX = "/dev/loop"


def die(msg):
    print(f"stand_gui: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        die("укажи устройство: python stand_gui.py /dev/loop0")
    disk = sys.argv[1]

    if os.environ.get("OUVERT_DISKMAP_SAMPLE"):
        die("OUVERT_DISKMAP_SAMPLE задан — чтение из файла и запись на диск "
            "одновременно запрещены.")
    if os.geteuid() != 0:
        die("нужен root: parted без него не работает.")
    if not disk.startswith(ALLOW_PREFIX):
        die(f"{disk} не похоже на loop-устройство. Стенд работает только "
            f"с {ALLOW_PREFIX}*, чтобы нельзя было промахнуться по живому диску.")
    allow = {x.strip() for x in
             os.environ.get("OUVERT_PARTOPS_ALLOW", "").split(",") if x.strip()}
    if disk not in allow:
        die(f"{disk} не в OUVERT_PARTOPS_ALLOW — кнопки всё равно будут серые. "
            f"Запусти так: sudo -E env OUVERT_PARTOPS_ALLOW={disk} "
            f"python stand_gui.py {disk}")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from PySide6.QtWidgets import QApplication

    import partedit
    import partops

    app = QApplication(sys.argv)
    ok, why = partops.write_allowed(disk)
    print(f"стенд: {disk}   запись разрешена: {ok}   {why}")

    dlg = partedit.PartitionEditor(disk)
    dlg.setWindowTitle(dlg.windowTitle() + "   [СТЕНД ЗАПИСИ]")
    dlg.exec()
    print("окно закрыто")


if __name__ == "__main__":
    main()
