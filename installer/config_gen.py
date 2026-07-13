"""Генерация конфигов для archinstall 4.4 (--config/--creds --silent).

Формат сверен с examples/config-sample.json и tests/data из исходников 4.4.
Разметка: GPT, ESP 1 GiB (fat32, /boot) + корень ext4 на остаток диска.
"""
import json
import os
import uuid
from pathlib import Path

from desktops import CUSTOM_SETTINGS

OUT_DIR = Path("/tmp/pzhavos")
CONFIG_PATH = OUT_DIR / "user_configuration.json"
CREDS_PATH = OUT_DIR / "user_credentials.json"


def _size(unit: str, value: int) -> dict:
    return {
        "sector_size": {"value": 512, "unit": "B"},
        "unit": unit,
        "value": value,
    }


def _partitions(disk_size_bytes: int) -> list[dict]:
    total_mib = disk_size_bytes // 2**20
    root_mib = max(total_mib - 1025 - 1, 1)  # минус ESP+старт и 1 MiB под хвост GPT
    esp = {
        "obj_id": str(uuid.uuid4()),
        "status": "create",
        "type": "primary",
        "fs_type": "fat32",
        "mountpoint": "/boot",
        "flags": ["boot", "esp"],
        "dev_path": None,
        "btrfs": [],
        "mount_options": [],
        "start": _size("MiB", 1),
        "size": _size("GiB", 1),
    }
    root = {
        "obj_id": str(uuid.uuid4()),
        "status": "create",
        "type": "primary",
        "fs_type": "ext4",
        "mountpoint": "/",
        "flags": [],
        "dev_path": None,
        "btrfs": [],
        "mount_options": [],
        "start": _size("MiB", 1025),
        "size": _size("MiB", root_mib),
    }
    return [esp, root]


def build_config(state: dict) -> dict:
    ru = state.get("lang") == "ru"
    profile = state["profile"]

    return {
        "version": "4.4",
        "archinstall-language": "English",
        "hostname": state.get("hostname") or "pzhavos",
        "kernels": ["linux"],
        "bootloader_config": {"bootloader": "Grub", "uki": False, "removable": True},
        "disk_config": {
            "config_type": "default_layout",
            "device_modifications": [
                {
                    "device": state["disk"],
                    "wipe": True,
                    "partitions": _partitions(int(state.get("disk_size") or 0)),
                }
            ],
        },
        "locale_config": {
            "kb_layout": "us",
            "sys_enc": "UTF-8",
            "sys_lang": "ru_RU" if ru else "en_US",
        },
        "network_config": {"type": "nm"},
        "audio_config": {"audio": "pipewire"},
        "profile_config": {
            "gfx_driver": "All open-source",
            "greeter": state["greeter"],
            "profile": {
                "main": "Desktop",
                "details": [profile],
                "custom_settings": CUSTOM_SETTINGS.get(profile, {}),
            },
        },
        "swap": {"enabled": True, "algorithm": "zstd"},
        "ntp": True,
        "timezone": "Europe/Moscow" if ru else "UTC",
        "packages": [],
        "pacman_config": {"color": True, "parallel_downloads": 5},
        "script": "guided",
    }


def build_creds(state: dict) -> dict:
    return {
        "users": [
            {
                "username": state["username"],
                "!password": state["password"],
                "sudo": True,
            }
        ]
    }


def write_configs(state: dict) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(build_config(state), indent=2, ensure_ascii=False))
    CREDS_PATH.write_text(json.dumps(build_creds(state), indent=2, ensure_ascii=False))
    os.chmod(CREDS_PATH, 0o600)
    return CONFIG_PATH, CREDS_PATH
