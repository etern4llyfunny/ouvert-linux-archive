#!/usr/bin/env python3
"""Патч 61: ungoogled-chromium-bin -> waterfox-bin.

Правит ОБЕ копии config_gen.py:
  ~/pzhavos/installer/config_gen.py
  ~/pzhavos/iso/profile/airootfs/opt/ouvert-installer/config_gen.py

Что делает:
  1) в списке пакетов: "ungoogled-chromium-bin" -> "waterfox-bin"
  2) блок enterprise-политики переписывает с chromium managed policy
     на waterfox policies.json (формат Firefox ESR).

Важно: /etc/waterfox/policies/policies.json ПЕРЕКРЫВАЕТ пакетный
/opt/waterfox/distribution/policies.json целиком, поэтому его ключи
(AppAutoUpdate/ManualAppUpdateOnly) продублированы в новом блоке —
иначе Waterfox начнёт сам себя обновлять в /opt, куда прав у него нет.

Идемпотентен: уже пропатченный файл пропускается.
Бэкап: <файл>.p61bak-<YYYYMMDD-HHMMSS>
"""

import os
import shutil
import sys
from datetime import datetime

FILES = [
    os.path.expanduser("~/pzhavos/installer/config_gen.py"),
    os.path.expanduser(
        "~/pzhavos/iso/profile/airootfs/opt/ouvert-installer/config_gen.py"
    ),
]

OLD_PKG = (
    '    "ungoogled-chromium-bin",  '
    "# conflicts=('chromium') — обычный chromium НЕ добавлять"
)
NEW_PKG = (
    '    "waterfox-bin",  '
    "# AUR, epoch 1; conflicts=('waterfox'), ставит /opt/waterfox"
)

BLOCK_START = "    # DuckDuckGo как поисковик по умолчанию в ungoogled-chromium."
BLOCK_END = '        "DDGEOF\\n"\n    )\n'

NEW_BLOCK = '''    # DuckDuckGo как поисковик по умолчанию в Waterfox.
    # Waterfox — форк Firefox ESR: поисковик задаётся enterprise-политикой
    # (policies.json), обычные preferences его не переключают.
    # ВАЖНО: /etc/waterfox/policies/policies.json перекрывает пакетный
    # /opt/waterfox/distribution/policies.json ЦЕЛИКОМ, поэтому ключи
    # AppAutoUpdate/ManualAppUpdateOnly продублированы здесь — без них
    # Waterfox полезет обновлять сам себя в /opt и будет ругаться.
    cmds.append(
        "set -e\\n"
        "mkdir -p /etc/waterfox/policies\\n"
        "cat > /etc/waterfox/policies/policies.json <<'DDGEOF'\\n"
        '{\\n'
        '  "policies": {\\n'
        '    "AppAutoUpdate": false,\\n'
        '    "ManualAppUpdateOnly": true,\\n'
        '    "SearchEngines": {\\n'
        '      "Default": "DuckDuckGo"\\n'
        '    }\\n'
        '  }\\n'
        '}\\n'
        "DDGEOF\\n"
    )
'''

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
changed = 0

for path in FILES:
    if not os.path.isfile(path):
        sys.exit(f"НЕТ ФАЙЛА: {path}")

    text = open(path, encoding="utf-8").read()

    if "waterfox-bin" in text and "ungoogled-chromium-bin" not in text:
        print(f"уже пропатчен, пропуск: {path}")
        continue

    if OLD_PKG not in text:
        sys.exit(f"не найдена строка пакета в {path}")
    if BLOCK_START not in text:
        sys.exit(f"не найден блок политики в {path}")

    start = text.index(BLOCK_START)
    end = text.index(BLOCK_END, start) + len(BLOCK_END)

    new_text = text[:start] + NEW_BLOCK + text[end:]
    new_text = new_text.replace(OLD_PKG, NEW_PKG)

    # проверки: ничего от chromium не осталось, файл валидный python
    assert "chromium" not in new_text, "остались упоминания chromium"
    assert "waterfox-bin" in new_text, "пакет не подставился"
    assert "/etc/waterfox/policies" in new_text, "путь политик не подставился"
    compile(new_text, path, "exec")

    backup = f"{path}.p61bak-{stamp}"
    shutil.copy2(path, backup)
    open(path, "w", encoding="utf-8").write(new_text)

    print(f"OK  {path}")
    print(f"    бэкап: {backup}")
    print(f"    было {len(text)} -> стало {len(new_text)} байт")
    changed += 1

print(f"\nпропатчено файлов: {changed}")

sizes = {os.path.getsize(p) for p in FILES}
print("размеры обеих копий совпадают" if len(sizes) == 1
      else f"ВНИМАНИЕ: размеры разошлись: {sizes}")
