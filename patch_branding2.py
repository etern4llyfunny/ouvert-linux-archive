#!/usr/bin/env python3
"""Патч 2 этапа 3: archinstall создаёт юзера ДО установки доп. пакетов
   (подтверждено логом t11: 23:28:30 Creating user admin ->
   23:30:07 Installing pzhavos-branding), поэтому skel-файлы пакета
   (конфиг fastfetch, README-zapret2) до первого юзера не доезжают.
   Фикс: в custom_commands (выполняются ПОСЛЕДНИМИ) докопировать
   их из /etc/skel в существующие /home/*.

   Запуск (ХОСТ): python patch_branding2.py
   Идемпотентен.
"""
from pathlib import Path
import sys

FILES = [
    Path("/home/admin/pzhavos/installer/config_gen.py"),
    Path("/home/admin/pzhavos/iso/profile/airootfs/opt/pzhavos-installer/config_gen.py"),
]

# Якорь — начало fastfetch-куска в DE-блоке (вставлен патчем 1).
ANCHOR = '        "printf \'\\\\n# PzhavOS\\\\ncommand -v fastfetch >/dev/null 2>&1 && fastfetch\\\\n\' >> /etc/skel/.bashrc\\n"\n'

ADDITION = '''\
        # Патч 2: юзер создаётся ДО установки пакетов (лог t11) ->
        # skel-файлы pzhavos-branding доезжают только до БУДУЩИХ юзеров.
        # Существующим докопируем вручную (без перезаписи, вдруг юзер свой).
        "for h in /home/*; do\\n"
        "  [ -d \\"$h\\" ] || continue\\n"
        "  u=$(basename \\"$h\\")\\n"
        "  if [ ! -e \\"$h/.config/fastfetch/config.jsonc\\" ]; then\\n"
        "    mkdir -p \\"$h/.config/fastfetch\\"\\n"
        "    cp /etc/skel/.config/fastfetch/config.jsonc \\"$h/.config/fastfetch/\\" || true\\n"
        "  fi\\n"
        "  [ -e \\"$h/README-zapret2.txt\\" ] || cp /etc/skel/README-zapret2.txt \\"$h/\\" || true\\n"
        "  chown -R \\"$u:$u\\" \\"$h/.config\\" \\"$h/README-zapret2.txt\\" 2>/dev/null || true\\n"
        "done\\n"
'''


def patch(path: Path) -> None:
    text = path.read_text()
    if "Патч 2:" in text:
        print(f"[SKIP] {path} — уже пропатчен")
        return
    assert text.count(ANCHOR) == 1, f"{path}: якорь fastfetch-printf не найден/неуникален"
    text = text.replace(ANCHOR, ADDITION + ANCHOR)
    path.write_text(text)
    print(f"[OK]   {path} — пропатчен")


def main() -> None:
    missing = [p for p in FILES if not p.exists()]
    if missing:
        for p in missing:
            print(f"[FAIL] нет файла: {p}")
        sys.exit(1)
    for p in FILES:
        patch(p)


if __name__ == "__main__":
    main()
