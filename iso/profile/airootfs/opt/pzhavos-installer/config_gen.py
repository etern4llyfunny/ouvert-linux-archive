"""Генерация конфигов для archinstall 4.4 (--config/--creds --silent).

ВЕРСИЯ: v4 (маркер для проверки свежести: grep VERSION config_gen.py)

Формат сверен ТОЛЬКО по исходникам archinstall тега 4.4:
  lib/models/device.py   DiskLayoutConfiguration.parse_arg, Size/SectorSize,
                         PartitionFlag, ModificationStatus, DiskEncryption.parse_arg
  lib/disk/disk_menu.py  suggest_single_disk_layout, _boot_partition,
                         get_default_btrfs_subvols
  lib/disk/filesystem.py форматируются только create+modify, existing не трогается
  lib/installer.py       _add_grub_bootloader: UEFI -> --target=<arch>-efi,
                         BIOS -> --target=i386-pc на родительский диск
  lib/models/bootloader.py  removable по умолчанию True (баг 7!)
  lib/args.py            --config и --creds мержатся в ОДИН dict,
                         encryption_password берётся оттуда же

Ключевые факты, из-за которых план раздела 9 был поправлен:
  * Флага bios_grub / EF02 в 4.4 НЕТ. Флаги только: boot, esp, bls_boot,
    linux-home, swap.
  * Таблица разделов в JSON не задаётся вообще: PartitionTable.default()
    выбирает GPT при UEFI и MBR (msdos) при BIOS по прошивке ЖИВОЙ системы.
  * Unit парсится как Unit[name] — регистр строгий: "MiB", "GiB", "B".
"""
import json
import os
import subprocess
import uuid
from pathlib import Path

from desktops import CUSTOM_SETTINGS

VERSION = "v4"

OUT_DIR = Path("/tmp/pzhavos")
CONFIG_PATH = OUT_DIR / "user_configuration.json"
CREDS_PATH = OUT_DIR / "user_credentials.json"

EFI_MARKER = Path("/sys/firmware/efi")

MIB = 2 ** 20
GIB = 2 ** 30

ESP_MIB = 1024        # archinstall: Size(1, Unit.GiB) под /boot
FIRST_START_MIB = 1   # archinstall: is_valid_start() требует >= 1 MiB
ROOT_START_MIB = FIRST_START_MIB + ESP_MIB

FILESYSTEMS = ["ext4", "btrfs", "xfs", "f2fs"]

# Точная копия get_default_btrfs_subvols() из archinstall 4.4
DEFAULT_SUBVOLS = [
    {"name": "@", "mountpoint": "/"},
    {"name": "@home", "mountpoint": "/home"},
    {"name": "@log", "mountpoint": "/var/log"},
    {"name": "@pkg", "mountpoint": "/var/cache/pacman/pkg"},
]

MOUNTPOINTS = ["/", "/boot", "/home", "swap"]


def is_uefi() -> bool:
    """UEFI или Legacy BIOS. От этого зависят флаги ESP и таблица разделов."""
    return EFI_MARKER.exists()


def detect_sector_size(disk: str) -> int:
    """Логический размер сектора. Хардкод 512 врёт на 4Kn-дисках."""
    try:
        out = subprocess.run(
            ["lsblk", "-J", "-d", "-b", "-o", "PATH,LOG-SEC", disk],
            capture_output=True, text=True, timeout=10,
        ).stdout
        devs = json.loads(out).get("blockdevices", [])
        if devs:
            return int(devs[0].get("log-sec") or 512)
    except Exception:
        pass
    return 512


def list_partitions(disk: str) -> list[dict]:
    """Существующие разделы диска для ручного режима.

    START — смещение в 512-байтных секторах (sysfs), всегда 512, независимо
    от LOG-SEC. Поэтому start_bytes = START * 512.
    """
    try:
        out = subprocess.run(
            ["lsblk", "-J", "-b", "-o", "PATH,SIZE,START,FSTYPE,TYPE,PARTTYPENAME", disk],
            capture_output=True, text=True, timeout=10,
        ).stdout
        tree = json.loads(out).get("blockdevices", [])
    except Exception:
        return []

    parts: list[dict] = []

    def walk(nodes):
        for n in nodes:
            if n.get("type") == "part":
                parts.append({
                    "path": n.get("path"),
                    "size": int(n.get("size") or 0),
                    "start": int(n.get("start") or 0) * 512,
                    "cur_fs": (n.get("fstype") or "").strip(),
                    "parttype": (n.get("parttypename") or "").strip(),
                    "mountpoint": None,
                    "format": False,
                    "fs": "ext4",
                })
            walk(n.get("children") or [])

    walk(tree)
    return parts


# --- примитивы JSON ---

def _sector(state: dict) -> dict:
    return {"value": int(state.get("sector_size") or 512), "unit": "B"}


def _size(state: dict, unit: str, value: int) -> dict:
    return {"value": int(value), "unit": unit, "sector_size": _sector(state)}


def _part(state: dict, **kw) -> dict:
    p = {
        "obj_id": str(uuid.uuid4()),
        "status": "create",
        "type": "primary",
        "fs_type": None,
        "mountpoint": None,
        "flags": [],
        "dev_path": None,
        "btrfs": [],
        "mount_options": [],
        "start": _size(state, "MiB", FIRST_START_MIB),
        "size": _size(state, "MiB", 1),
    }
    p.update(kw)
    return p


def _mount_options(state: dict) -> list[str]:
    if state.get("fs") == "btrfs" and state.get("btrfs_compress", True):
        return ["compress=zstd"]  # BtrfsMountOption.compress
    return []


def use_subvols(state: dict) -> bool:
    return state.get("fs") == "btrfs" and bool(state.get("btrfs_subvols", True))


def use_separate_home(state: dict) -> bool:
    # archinstall сам исключает /home при сабволюмах — @home их заменяет
    return bool(state.get("separate_home")) and not use_subvols(state)


def available_mib(state: dict) -> int:
    """Полезное место с учётом резерва под backup-заголовок GPT."""
    total_mib = int(state.get("disk_size") or 0) // MIB
    return total_mib - 1 if is_uefi() else total_mib


def max_root_gib(state: dict) -> int:
    """Максимум под корень, когда /home отдельным разделом (мин. 8 GiB под /home)."""
    return max(1, (available_mib(state) - ROOT_START_MIB - 8 * 1024) // 1024)


# --- режим «Стереть диск» ---

def _wipe_partitions(state: dict) -> list[dict]:
    uefi = is_uefi()
    avail_mib = available_mib(state)
    fs = state.get("fs") or "ext4"
    subvols = use_subvols(state)
    sep_home = use_separate_home(state)

    # _boot_partition() из archinstall: fat32, /boot, 1 GiB, старт 1 MiB,
    # флаг esp добавляется ТОЛЬКО при GPT (то есть при UEFI). Баг 6: без esp
    # is_efi() не находит раздел -> "Could not detect efi partition".
    boot = _part(
        state,
        fs_type="fat32",
        mountpoint="/boot",
        flags=["boot", "esp"] if uefi else ["boot"],
        start=_size(state, "MiB", FIRST_START_MIB),
        size=_size(state, "MiB", ESP_MIB),
    )

    if sep_home:
        root_mib = int(state.get("root_size_gib") or 40) * 1024
    else:
        root_mib = avail_mib - ROOT_START_MIB
    root_mib = max(root_mib, 1)

    root = _part(
        state,
        fs_type=fs,
        mountpoint=None if subvols else "/",
        btrfs=list(DEFAULT_SUBVOLS) if subvols else [],
        mount_options=_mount_options(state),
        start=_size(state, "MiB", ROOT_START_MIB),
        size=_size(state, "MiB", root_mib),
    )

    parts = [boot, root]

    if sep_home:
        home_start = ROOT_START_MIB + root_mib
        home_mib = max(avail_mib - home_start, 1)
        parts.append(_part(
            state,
            fs_type=fs,
            mountpoint="/home",
            flags=["linux-home"] if uefi else [],  # флаг только для GPT
            mount_options=_mount_options(state),
            start=_size(state, "MiB", home_start),
            size=_size(state, "MiB", home_mib),
        ))

    return parts


# --- режим «Вручную» ---

def _manual_partitions(state: dict) -> list[dict]:
    """Существующие разделы. status:
         existing — примонтировать как есть, НЕ форматировать
         modify   — отформатировать (filesystem.py: create+modify)
       dev_path обязателен для обоих, fs_type обязателен для modify.
       Разделы без точки монтирования в конфиг не попадают вообще.
    """
    uefi = is_uefi()
    out: list[dict] = []

    for p in state.get("manual_parts") or []:
        mp = p.get("mountpoint")
        if not mp:
            continue

        fmt = bool(p.get("format"))
        flags: list[str] = []

        if mp == "swap":
            fs_type = "linux-swap"
            mountpoint = None
            flags = ["swap"]
        else:
            fs_type = (p.get("fs") if fmt else p.get("cur_fs")) or "ext4"
            mountpoint = mp
            if mp == "/boot" and uefi:
                # Иначе снова "Could not detect efi partition" (баг 6)
                flags = ["boot", "esp"]
            elif mp == "/boot":
                flags = ["boot"]

        out.append(_part(
            state,
            status="modify" if fmt else "existing",
            fs_type=fs_type,
            mountpoint=mountpoint,
            dev_path=p["path"],
            flags=flags,
            mount_options=["compress=zstd"] if (fmt and fs_type == "btrfs") else [],
            start=_size(state, "B", int(p.get("start") or 0)),
            size=_size(state, "B", int(p.get("size") or 0)),
        ))

    return out


# --- сборка disk_config ---

def build_disk_config(state: dict) -> dict:
    if state.get("part_mode") == "manual":
        return {
            "config_type": "manual_partitioning",
            "device_modifications": [{
                "device": state["disk"],
                "wipe": False,
                "partitions": _manual_partitions(state),
            }],
        }

    parts = _wipe_partitions(state)
    cfg = {
        "config_type": "default_layout",
        "device_modifications": [{
            "device": state["disk"],
            "wipe": True,
            "partitions": parts,
        }],
    }

    if state.get("luks") and state.get("luks_password"):
        # Шифруем всё, кроме /boot. Для /home archinstall сам сгенерит keyfile,
        # корень спросит пароль на загрузке (хуки encrypt + cryptdevice=... —
        # installer.py делает это сам).
        enc = [p["obj_id"] for p in parts if p["mountpoint"] != "/boot"]
        cfg["disk_encryption"] = {
            "encryption_type": "luks",
            "partitions": enc,
            "lvm_volumes": [],
        }

    return cfg


def build_config(state: dict) -> dict:
    ru = state.get("lang") == "ru"
    profile = state["profile"]

    return {
        "version": "4.4",
        "archinstall-language": "English",
        "hostname": state.get("hostname") or "pzhavos",
        "kernels": ["linux"],
        # removable=True — fallback /EFI/BOOT/BOOTX64.EFI. Баг 7: без него
        # система не грузится после сброса NVRAM. В v3 стояло False.
        "bootloader_config": {"bootloader": "Grub", "uki": False, "removable": True},
        "disk_config": build_disk_config(state),
        "locale_config": {
            "kb_layout": "us",
            "sys_enc": "UTF-8",
            "sys_lang": "ru_RU" if ru else "en_US",
        },
        "network_config": {"type": "nm"},
        "app_config": {
            "audio_config": {"audio": "pipewire"},
            "bluetooth_config": {"enabled": True},
            "print_service_config": {"enabled": True},
        },
        "mirror_config": {"optional_repositories": state.get("repos") or []},
        "profile_config": {
            "gfx_driver": state.get("gfx") or "All open-source",
            "greeter": state["greeter"],
            "profile": {
                "main": "Desktop",
                "details": [profile],
                "custom_settings": CUSTOM_SETTINGS.get(profile, {}),
            },
        },
        "swap": {"enabled": True, "algorithm": "zstd"},
        "ntp": True,
        "timezone": state.get("timezone") or ("Europe/Moscow" if ru else "UTC"),
        "packages": [],
        "pacman_config": {"color": True, "parallel_downloads": 5},
        "script": "guided",
    }


def build_creds(state: dict) -> dict:
    creds: dict = {
        "users": [
            {
                "username": state["username"],
                "!password": state["password"],
                "sudo": True,
            }
        ]
    }
    # args.py: config.update(creds) — ключ читается из общего словаря.
    # Без пароля DiskEncryption.parse_arg молча вернёт None (шифрования не будет).
    if state.get("part_mode") != "manual" and state.get("luks") and state.get("luks_password"):
        creds["encryption_password"] = state["luks_password"]
    return creds


def write_configs(state: dict) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(build_config(state), indent=2, ensure_ascii=False))
    CREDS_PATH.write_text(json.dumps(build_creds(state), indent=2, ensure_ascii=False))
    os.chmod(CREDS_PATH, 0o600)
    return CONFIG_PATH, CREDS_PATH
