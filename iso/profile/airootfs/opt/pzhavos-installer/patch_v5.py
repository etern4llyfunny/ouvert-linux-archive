#!/usr/bin/env python3
"""
Патч config_gen.py: v4 -> v5 (репозиторий pzhavos + предустановка приложений).

Запускать ИЗ ~/pzhavos/installer:
    python patch_v5.py

Скрипт делает точечные замены и падает, если ожидаемый кусок не найден
или найден не один раз. Ничего не портит молча. Бэкап: config_gen.py.v4.bak
"""

import sys
from pathlib import Path

p = Path("config_gen.py")
if not p.exists():
    sys.exit("ОШИБКА: config_gen.py не найден. Запускай из ~/pzhavos/installer")

src = p.read_text()


def sub(old: str, new: str, what: str) -> None:
    global src
    n = src.count(old)
    if n != 1:
        sys.exit(f"ОШИБКА [{what}]: найдено вхождений: {n}, ожидалось 1. Патч НЕ применён.")
    src = src.replace(old, new)


# ── 1. Маркер версии ────────────────────────────────────────────────────
sub('ВЕРСИЯ: v4 (маркер', 'ВЕРСИЯ: v5 (маркер', "шапка")
sub('VERSION = "v4"', 'VERSION = "v5"', "VERSION")

# ── 2. Константы репо и списки пакетов (перед build_config) ─────────────
BLOCK = '''# ── ЭТАП 2Б: РЕПОЗИТОРИЙ PZHAVOS И ПРЕДУСТАНОВКА ──────────────────────
#
# Репозиторий едет в ISO (build.sh кладёт его в airootfs/opt/pzhavos-repo),
# поэтому в ЖИВОЙ системе он доступен как обычный каталог.
#
# Как это работает (проверено по исходникам archinstall 4.4):
#   guided.py:101  set_mirrors(on_target=False) -> дописывает [pzhavos]
#                  в pacman.conf ЖИВОЙ системы;
#   pacman.py:111  pacstrap -C /etc/pacman.conf -> ВСЕГДА конфиг живой
#                  системы, и для base, и для add_additional_packages,
#                  значит наши пакеты видны;
#   installer.py:953 PacmanConfig.persist() -> КОПИРУЕТ живой pacman.conf
#                  в цель целиком (вместе с [pzhavos]);
#   guided.py:112  set_mirrors(on_target=True) -> дописывает [pzhavos]
#                  в цель ВТОРОЙ раз.
# Итог: в целевом pacman.conf два блока [pzhavos] с путём file:///opt/...,
# которого после перезагрузки не существует. Поэтому build_custom_commands
# ОБЯЗАН вычистить секцию — иначе у юзера падает pacman -Syu.
REPO_NAME = "pzhavos"
REPO_DIR = "/opt/pzhavos-repo/x86_64"
REPO_URL = f"file://{REPO_DIR}"

# Пакеты не подписаны -> SigLevel = Never TrustAll.
# Значения строгие, это энумы SignCheck/SignOption (lib/models/mirrors.py).
CUSTOM_REPOS = [
    {
        "name": REPO_NAME,
        "url": REPO_URL,
        "sign_check": "Never",
        "sign_option": "TrustAll",
    }
]

# Предустановка. Из нашего репо приедут и зависимости (python-steam и др.).
PACKAGES = [
    # наш репозиторий
    "ungoogled-chromium-bin",  # conflicts=('chromium') — обычный chromium НЕ добавлять
    "v2raya",
    "zapret2",
    "protonup-qt",
    "paru",
    "pzhavmem",
    # официальные репозитории
    "kitty",
    "kate",
    "fastfetch",
    "cmatrix",
    "cava",
    "git",
    "flatpak",
    "ipset",  # optdepends zapret2: нужен для режима iptables
]

# Требуют multilib. Если юзер снял галку — steam просто не поставится,
# а установка упала бы целиком на "target not found".
PACKAGES_MULTILIB = ["steam"]


def build_packages(state: dict) -> list[str]:
    pkgs = list(PACKAGES)
    if "multilib" in (state.get("repos") or []):
        pkgs += PACKAGES_MULTILIB
    return pkgs


'''

sub("def build_config(state: dict) -> dict:", BLOCK + "def build_config(state: dict) -> dict:", "блок констант")

# ── 3. custom_commands: чистка pacman.conf + flathub ────────────────────
CMDS = '''        )

    # Чистка секции [pzhavos] из pacman.conf ЦЕЛИ. Блоков там ДВА
    # (см. комментарий у CUSTOM_REPOS). Каждый — ровно 3 строки:
    #   [pzhavos] / SigLevel = ... / Server = ...
    # (repositories_config(), lib/models/mirrors.py). Диапазон /re/,+2
    # sed применяет к каждому совпадению, так что уйдут оба.
    # Без этого pacman -Syu у юзера падает: file:///opt/pzhavos-repo
    # после перезагрузки не существует.
    # Бонус: пакеты становятся foreign -> paru видит для них обновления
    # в AUR. Если оставить [pzhavos], paru счёл бы их реповыми и не
    # обновлял бы никогда.
    cmds.append(
        "set -e\\n"
        f"sed -i '/^\\\\[{REPO_NAME}\\\\]$/,+2d' /etc/pacman.conf\\n"
    )

    # Flathub. Без || true падение (нет сети) уронило бы всю установку:
    # run_custom_user_commands не ловит ошибки (installer.py:2141).
    cmds.append(
        "flatpak remote-add --if-not-exists flathub "
        "https://dl.flathub.org/repo/flathub.flatpakrepo || true\\n"
    )

    return cmds'''

sub("        )\n    return cmds", CMDS, "custom_commands")

# ── 4. mirror_config: добавляем custom_repositories ─────────────────────
sub(
    '"mirror_config": {"optional_repositories": state.get("repos") or []},',
    '"mirror_config": {\n'
    '            "optional_repositories": state.get("repos") or [],\n'
    '            "custom_repositories": CUSTOM_REPOS,\n'
    "        },",
    "mirror_config",
)

# ── 5. packages ─────────────────────────────────────────────────────────
sub('"packages": [],', '"packages": build_packages(state),', "packages")

# ── Запись ──────────────────────────────────────────────────────────────
Path("config_gen.py.v4.bak").write_text(p.read_text())
p.write_text(src)
print("OK: config_gen.py пропатчен до v5. Бэкап: config_gen.py.v4.bak")
