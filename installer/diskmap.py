"""
diskmap.py — чтение карты диска для редактора разделов (этап 5, шаг 3).
ТОЛЬКО ЧТЕНИЕ. Ни одной операции записи.

Источник истины: parted -m <disk> unit B print free
  ОБЯЗАТЕЛЬНО под LC_ALL=C — иначе флаги локализуются
  ("скрытый" вместо "hidden") и эвристика Recovery ломается молча.
"""

import json
import os
import subprocess
import tempfile

# Свободные блоки меньше этого не показываем: это зазоры GPT и выравнивание,
# а не пригодное место. 2 МиБ.
FREE_MIN_BYTES = 2 * 1024 * 1024


def _run(cmd):
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=15,
        env={"LC_ALL": "C", "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
    ).stdout


def parse_parted(text: str) -> dict:
    """Разбирает машинный вывод parted -m. Возвращает {disk:..., items:[...]}."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines or lines[0] != "BYT;":
        return {"disk": None, "items": []}

    head = lines[1].rstrip(";").split(":")
    disk = {
        "path": head[0],
        "size": _b(head[1]),
        "transport": head[2] if len(head) > 2 else "",
        "logical_sector": int(head[3]) if len(head) > 3 else 512,
        "physical_sector": int(head[4]) if len(head) > 4 else 512,
        "table": head[5] if len(head) > 5 else "",
        "model": head[6] if len(head) > 6 else "",
    }

    items = []
    for line in lines[2:]:
        f = line.rstrip(";").split(":")
        if len(f) < 5:
            continue
        start, end, size = _b(f[1]), _b(f[2]), _b(f[3])

        # СВОБОДНЫЙ БЛОК: опознаётся ТОЛЬКО по маркеру 'free' в 5-м поле.
        # По номеру — НЕЛЬЗЯ: parted пишет всем свободным блокам номер 1,
        # и настоящий раздел №1 от них так не отличить.
        if f[4] == "free":
            items.append({
                "kind": "free",
                "path": None,
                "number": None,
                "start": start, "end": end, "size": size,
                "fstype": "", "name": "", "flags": [],
            })
            continue

        flags = [x.strip() for x in (f[6] if len(f) > 6 else "").split(",") if x.strip()]
        items.append({
            "kind": "part",
            "path": part_path(disk["path"], f[0]),
            "number": int(f[0]),
            "start": start, "end": end, "size": size,
            "fstype": f[4],
            "name": f[5] if len(f) > 5 else "",
            "flags": flags,
        })

    # Сортировка ПО СМЕЩЕНИЮ, а не по номеру (ТЗ 5.7: номера не последовательны).
    items.sort(key=lambda i: i["start"])
    return {"disk": disk, "items": items}


def part_path(disk: str, number) -> str:
    """Bug 36: путь раздела НЕ равен «диск + номер».
    Ядро вставляет 'p', когда имя диска кончается цифрой:
        /dev/sda      -> /dev/sda1
        /dev/vda      -> /dev/vda1
        /dev/nvme0n1  -> /dev/nvme0n1p1
        /dev/mmcblk0  -> /dev/mmcblk0p1
        /dev/loop0    -> /dev/loop0p1
    Правило ЛЕКСИЧЕСКОЕ, а не по наличию файла: карта должна одинаково
    строиться и для реального диска, и для слепка в режиме стенда.
    """
    d = str(disk)
    return f"{d}p{number}" if d and d[-1].isdigit() else f"{d}{number}"


def _b(s: str) -> int:
    return int(str(s).rstrip("B") or 0)


def visible_items(m: dict) -> list:
    """Отсекает мусорные свободные блоки (зазоры GPT, выравнивание)."""
    return [i for i in m["items"]
            if i["kind"] != "free" or i["size"] >= FREE_MIN_BYTES]


def describe(item: dict, ctx: dict) -> str:
    """Колонка «ЧТО ЭТО» (ТЗ 5.3).
    СЛОЯМИ: флаги -> ФС -> имя раздела. Опираться ТОЛЬКО на fstype нельзя:
    на реальном стенде t26 разделы Windows и Recovery не имели ФС вовсе
    и опознавались исключительно по флагам msftdata / hidden+diag.
    """
    if item["kind"] == "free":
        return "Свободно"

    flags = set(item["flags"])
    fs = (item["fstype"] or "").lower()
    name = (item["name"] or "").strip()

    # --- слой 1: флаги ---
    if "msftres" in flags:
        return "Служебный раздел Windows"
    if {"hidden", "diag"} & flags:
        return "Восстановление Windows"
    # ESP: флага esp МАЛО. На GPT parted ставит один и тот же GUID и для
    # 'boot', и для 'esp', поэтому ext4-раздел /boot тоже носит esp
    # (проверено на t26: vda6 ext4 с флагами boot,esp). Требуем ещё FAT.
    if "esp" in flags and fs.startswith("fat"):
        if ctx.get("ms_boot", {}).get(item["path"]) is True:
            return "Загрузчик Windows (EFI)"
        return "Загрузчик EFI"

    # --- слой 2: файловая система ---
    if fs == "ntfs":
        if item["size"] > 50 * 1024**3:
            return "Windows (данные)"
        return "Раздел Windows"
    if fs in ("ext2", "ext3", "ext4", "btrfs", "xfs", "f2fs"):
        return f"Linux ({fs})"
    if fs.startswith("linux-swap"):
        return "Подкачка"

    # --- слой 3: флаг данных Windows / имя раздела ---
    if "msftdata" in flags:
        if item["size"] > 50 * 1024**3:
            return "Windows (данные)"
        return "Раздел данных Windows"
    if name:
        return f"Раздел «{name}»"
    if not fs:
        return "Без файловой системы"
    return fs


def _ci_lookup(base: str, name: str):
    """Регистронезависимый поиск элемента в каталоге."""
    try:
        for e in os.listdir(base):
            if e.lower() == name.lower():
                return os.path.join(base, e)
    except OSError:
        pass
    return None


def _has_windows_loader(dev: str):
    """Монтирует раздел ТОЛЬКО НА ЧТЕНИЕ и ищет загрузчик Windows.
    True  — загрузчик найден
    False — раздел проверен, загрузчика нет
    None  — ПРОВЕРИТЬ НЕ УДАЛОСЬ (не смонтировался и т.п.)
    ★ None трактуется как «защищён»: отказ проверки не должен
      превращаться в разрешение удалить чужой загрузчик.
    """
    tmp = tempfile.mkdtemp(prefix="ouvert-esp-")
    try:
        r = subprocess.run(
            ["mount", "-o", "ro,nosuid,nodev,noexec", dev, tmp],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return None
        cur = tmp
        for part in ("EFI", "Microsoft", "Boot", "bootmgfw.efi"):
            cur = _ci_lookup(cur, part)
            if cur is None:
                return False
        return True
    except Exception:
        return None
    finally:
        subprocess.run(["umount", tmp], capture_output=True, timeout=15)
        try:
            os.rmdir(tmp)
        except OSError:
            pass


def build_context(m: dict, probe=None) -> dict:
    """probe — функция проверки загрузчика (подменяется в тестах)."""
    if probe is None:
        probe = _has_windows_loader
    esp = [i for i in m["items"]
           if i["kind"] == "part"
           and "esp" in set(i["flags"])
           and (i["fstype"] or "").lower().startswith("fat")]
    ms_boot = {i["path"]: probe(i["path"]) for i in esp}
    return {
        "esp_count": len(esp),
        "esp_paths": {i["path"] for i in esp},
        "ms_boot": ms_boot,
    }


# ФС, на которых может жить корень. Всё остальное под «/» — отказ,
# а не предупреждение: archinstall просто не поставит туда систему.
LINUX_FS = frozenset(("ext2", "ext3", "ext4", "btrfs", "xfs", "f2fs"))

# Bug 32/33: у FAT три разных имени в трёх разных местах — lsblk зовёт
# его vfat, parted пишет fat32, в списке установщика тоже fat32.
# ★ Дубль этого списка живёт в partitioning.py (_is_fat): та страница
#   обязана работать, даже если diskmap не уехал в сборку. При правке
#   менять ОБА места.
FAT_FS = ("fat", "vfat", "msdos")


def is_fat(fs: str) -> bool:
    return (fs or "").lower().startswith(FAT_FS)

# Bug 23: загрузчику нужно место на ESP. 20 МиБ — с запасом на два ядра.
ESP_MIN_FREE = 20 * 1024 * 1024


def can_format(item: dict, ctx: dict) -> tuple[bool, str]:
    """УРОВЕНЬ 1, форматирование (Bug 31).

    Форматирование по последствиям равно удалению, поэтому запреты те же —
    КРОМЕ «единственный ESP»: единственный ESP БЕЗ загрузчика Windows
    отформатировать под /efi как раз нормально, это обычная установка.
    """
    if item["kind"] == "free":
        return False, "Это свободное место"
    flags = set(item["flags"])
    if "msftres" in flags:
        return False, "Служебный раздел Windows (MSR)"
    if {"hidden", "diag"} & flags:
        return False, "Раздел восстановления Windows"
    if item.get("mounted"):
        return False, "Раздел примонтирован"

    ms = ctx.get("ms_boot", {})
    if item["path"] in ms:
        state = ms[item["path"]]
        if state is True:
            return False, "Здесь лежит загрузчик Windows"
        if state is None:
            return False, "Не удалось проверить содержимое EFI-раздела"
    return True, ""


def can_delete(item: dict, ctx: dict) -> tuple[bool, str]:
    """УРОВЕНЬ 1 из ТЗ 5.4 — ЗАПРЕТ. Возвращает (можно?, причина).

    Делает всё, что can_format, плюс один свой запрет. Специально
    выражен ЧЕРЕЗ can_format: два независимых списка запретов рано или
    поздно разъедутся, и разъедутся молча.
    """
    ok, why = can_format(item, ctx)
    if not ok:
        return ok, why
    if item["path"] in ctx.get("ms_boot", {}) and ctx.get("esp_count", 0) <= 1:
        return False, "Единственный EFI-раздел на диске"
    return True, ""


def free_bytes(dev: str):
    """Свободно байт на разделе; None — измерить не удалось (Bug 23).
    Монтирует ТОЛЬКО НА ЧТЕНИЕ и обязательно отмонтирует за собой.
    """
    tmp = tempfile.mkdtemp(prefix="ouvert-free-")
    try:
        r = subprocess.run(
            ["mount", "-o", "ro,nosuid,nodev,noexec", dev, tmp],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return None
        st = os.statvfs(tmp)
        return st.f_bavail * st.f_frsize
    except Exception:
        return None
    finally:
        subprocess.run(["umount", tmp], capture_output=True, timeout=15)
        try:
            os.rmdir(tmp)
        except OSError:
            pass


def mount_target(dev: str) -> str:
    """Куда примонтирован раздел; пустая строка — не примонтирован.
    findmnt возвращает НЕнулевой код, когда ничего не нашёл, — это норма,
    поэтому смотрим только stdout. LC_ALL=C приходит из _run().
    """
    out = _run(["findmnt", "-rn", "-o", "TARGET", "-S", dev])
    return ", ".join(l.strip() for l in out.splitlines() if l.strip())


def fill_mounted(m: dict) -> dict:
    """Проставляет item['mounted'] — вход для can_delete (ТЗ 5.7)."""
    for it in m.get("items", []):
        if it["kind"] == "part" and it.get("path"):
            it["mounted"] = mount_target(it["path"])
    return m


def human(n: int) -> str:
    """ТЗ/Bug 29: мелкие разделы не должны показываться как 0.0 GiB."""
    if n >= 1024**3:
        return f"{n / 1024**3:.1f} ГиБ"
    if n >= 1024**2:
        return f"{n / 1024**2:.0f} МиБ"
    return f"{n} Б"


def read_disk(disk: str) -> dict:
    return parse_parted(_run(["parted", "-m", disk, "unit", "B", "print", "free"]))
