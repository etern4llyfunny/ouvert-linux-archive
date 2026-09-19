#!/usr/bin/env python3
from pathlib import Path

FILES = [
    Path.home() / "pzhavos/iso/profile/airootfs/opt/pzhavos-installer/config_gen.py",
    Path.home() / "pzhavos/installer/config_gen.py",
]

ANCHOR = '''    # Flathub. Без || true падение (нет сети) уронило бы всю установку:
    # run_custom_user_commands не ловит ошибки (installer.py:2141).
    cmds.append(
        "flatpak remote-add --if-not-exists flathub "
        "https://dl.flathub.org/repo/flathub.flatpakrepo || true\\n"
    )
'''

INSERT = '''    # DuckDuckGo как поисковик по умолчанию в ungoogled-chromium.
    # ungoogled ВЫПИЛИ дефолтные движки -> обычные preferences не помогут.
    # Рабочий путь - enterprise policy managed. Движок ПРИНУДИТЕЛЬНЫЙ.
    cmds.append(
        "set -e\\n"
        "mkdir -p /etc/chromium/policies/managed\\n"
        "cat > /etc/chromium/policies/managed/pzhavos-search.json <<'DDGEOF'\\n"
        '{\\n'
        '  "DefaultSearchProviderEnabled": true,\\n'
        '  "DefaultSearchProviderName": "DuckDuckGo",\\n'
        '  "DefaultSearchProviderSearchURL": "https://duckduckgo.com/?q={searchTerms}",\\n'
        '  "DefaultSearchProviderSuggestURL": "https://duckduckgo.com/ac/?q={searchTerms}&type=list"\\n'
        '}\\n'
        "DDGEOF\\n"
    )
'''

for f in FILES:
    src = f.read_text()
    n = src.count(ANCHOR)
    assert n == 1, f"{f.name}: anchor found {n} times (expected 1). SKIP."
    assert "pzhavos-search.json" not in src, f"{f.name}: already patched. SKIP."
    f.write_text(src.replace(ANCHOR, ANCHOR + "\n" + INSERT))
    print(f"OK: {f}")

print("Done. Both copies synced.")
