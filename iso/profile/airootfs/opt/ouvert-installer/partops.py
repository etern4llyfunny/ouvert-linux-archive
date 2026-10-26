"""
partops.py — ЕДИНСТВЕННОЕ МЕСТО В ПРОЕКТЕ, КОТОРОЕ ПИШЕТ НА ДИСК.
Этап 5, сессия 3. Две операции: create() и delete(). Больше ничего.

ЧЕГО ЗДЕСЬ НЕТ И НЕ БУДЕТ (решено заранее, п. 10.6 выжимки v18):
  изменения размера существующих разделов. ntfsresize — отдельная
  большая задача с реальным риском потерять ЧУЖИЕ данные.

ПОЧЕМУ НЕ ИМПОРТИРУЕТ partedit:
  partedit тянет PySide6. Если бы запись зависела от него, каждый тест
  записи требовал бы Qt. Сброс кэшей (partedit.forget) — обязанность GUI,
  который вызывает эти функции, а не самого модуля записи.

ГЕЙТ ЗАПИСИ (п. 10.1). Живёт ЗДЕСЬ, а не в кнопке: кнопку можно обойти,
модуль — нет. Условия проверяются на КАЖДУЮ операцию, не один раз:
    Path("/run/archiso").exists()   загрузились с ISO, а не с рабочей ОС
  И os.geteuid() == 0               parted без root бесполезен
  И НЕ задан OUVERT_DISKMAP_SAMPLE   стенд подменяет ЧТЕНИЕ; писать при
                                    подменённых данных нельзя никогда

OUVERT_PARTOPS_ALLOW=/dev/loop0[,...] — БЕЛЫЙ СПИСОК ДЛЯ ОТЛАДКИ.
  Снимает ТОЛЬКО требование /run/archiso и ТОЛЬКО для точно названных
  устройств. root по-прежнему обязателен, стенд по-прежнему запрещён,
  любое устройство вне списка по-прежнему недоступно.
  Нужен, чтобы гонять create/delete на loop-файле, а не в ВМ.

★ ЛОВУШКА msftdata — ПРОВЕРЕНО ЗАПУСКОМ parted 3.6, НЕ ПО ПАМЯТИ:
  mkpart с типом fat32 или ntfs получает флаг msftdata; с типом ext4 —
  не получает (там свой Linux-GUID). Слой 3 в diskmap.describe()
  превращает msftdata в «Раздел данных Windows».
  СЛЕДСТВИЕ: FAT32 БЕЗ флага esp показывается пользователю как
  «Раздел данных Windows». Поэтому esp взводится ДО mkfs, а сам флаг
  esp вытесняет msftdata (parted меняет GUID типа целиком).
  Для ext4 ловушки нет — исходная гипотеза была шире правды.

★ ИМЯ РАЗДЕЛА ЗАВИСИТ ОТ ТАБЛИЦЫ, ХАРДКОДИТЬ НЕЛЬЗЯ:
  на msdos аргумент mkpart — это ТИП и обязан быть primary/logical;
  на gpt тот же аргумент — это ИМЯ раздела, и слово "primary" уезжает
  пользователю на экран как «Раздел «primary»». Отсюда _part_arg().
"""

import os
import re
import stat
import subprocess
import time
from pathlib import Path

import diskmap

VERSION = "partops-v1"

LIVE_MARKER = Path("/run/archiso")

# Выравнивание начала раздела. -a optimal добивает остальное.
ALIGN = 1024 * 1024
# Меньше этого создавать бессмысленно: ESP по спецификации от 100 МиБ,
# всё мельче — почти наверняка промах пользователя.
MIN_CREATE = 8 * 1024 * 1024

# Аргумент ФС для `parted mkpart`. НЕ создаёт файловую систему: на GPT это
# лишь подсказка типа раздела. parted 3.6 не знает f2fs и упадёт на нём,
# поэтому всё неизвестное отображаем в ext4 — тип GUID у них общий,
# а настоящую ФС делает mkfs ниже.
_PTYPE = {
    "fat32": "fat32", "fat16": "fat16", "vfat": "fat32", "fat": "fat32",
    "ntfs": "ntfs",
    "linux-swap": "linux-swap", "swap": "linux-swap",
}

_MKFS = {
    "fat32": ["mkfs.fat", "-F32"],
    "vfat": ["mkfs.fat", "-F32"],
    "fat": ["mkfs.fat", "-F32"],
    "ext2": ["mkfs.ext2", "-F"],
    "ext3": ["mkfs.ext3", "-F"],
    "ext4": ["mkfs.ext4", "-F"],
    "btrfs": ["mkfs.btrfs", "-f"],
    "xfs": ["mkfs.xfs", "-f"],
    "f2fs": ["mkfs.f2fs", "-f"],
    "linux-swap": ["mkswap"],
    "swap": ["mkswap"],
}

_ENV = {"LC_ALL": "C", "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}


class PartOpError(Exception):
    """Любой отказ операции записи. Текст пригоден для показа человеку."""


# ───────────────────────────── гейт ─────────────────────────────

def _allow_list() -> set:
    raw = os.environ.get("OUVERT_PARTOPS_ALLOW", "")
    return {x.strip() for x in raw.split(",") if x.strip()}


def write_allowed(disk: str) -> tuple[bool, str]:
    """(можно?, причина отказа). Причина — готовый текст для человека."""
    if os.environ.get("OUVERT_DISKMAP_SAMPLE"):
        return False, ("Включён режим стенда: данные берутся из файла, "
                       "а не с диска. Запись запрещена.")
    if os.geteuid() != 0:
        return False, "Для изменения разделов нужны права root."

    allow = _allow_list()
    if allow:
        if disk in allow:
            return True, ""
        return False, (f"Устройство {disk} не входит в список разрешённых "
                       f"для отладки (OUVERT_PARTOPS_ALLOW).")

    if not LIVE_MARKER.exists():
        return False, ("Изменять разделы можно только при загрузке с диска "
                       "Ouvert Linux, а не из установленной системы.")
    return True, ""


def _require(disk: str) -> None:
    ok, why = write_allowed(disk)
    if not ok:
        raise PartOpError(why)
    try:
        if not stat.S_ISBLK(os.stat(disk).st_mode):
            raise PartOpError(f"{disk} — не блочное устройство.")
    except FileNotFoundError:
        raise PartOpError(f"Устройство {disk} не найдено.")
    if re.search(r"(\d|p\d+)$", disk) and not re.search(r"loop\d+$", disk):
        # /dev/sda1 вместо /dev/sda — почти наверняка ошибка вызывающего
        raise PartOpError(f"{disk} похоже на раздел, а не на диск.")


# ─────────────────────────── утилиты ────────────────────────────

def _part_arg(table: str, fs_key: str, want_esp: bool, name=None) -> str:
    """Первый аргумент mkpart. ПРОВЕРЕНО ЗАПУСКОМ parted 3.6:
      msdos: это ТИП, обязан быть primary/logical. Пустая строка →
             «Error: Expecting a partition type».
      gpt:   это ИМЯ. Пустая строка НЕ означает «без имени» — parted
             молча СДВИГАЕТ аргументы и съедает подсказку fs-type
             (mkpart "" fat32 → имя стало «fat32», тип потерян).
             Очистить имя потом тоже нельзя: `parted name N ""`
             отрабатывает БЕЗ ОШИБКИ И БЕЗ ЭФФЕКТА.
    Поэтому на gpt имя всегда непустое и осмысленное — его видно
    пользователю в колонке «Имя»."""
    if (table or "").lower() in ("msdos", "mbr"):
        return "primary"
    if name:
        return str(name)
    if want_esp:
        return "EFI"
    if fs_key in ("swap", "linux-swap"):
        return "swap"
    return "Linux"


def _run(cmd: list, what: str, timeout: int = 120) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, env=_ENV)
    except FileNotFoundError:
        raise PartOpError(f"{what}: программа {cmd[0]} не найдена.")
    except subprocess.TimeoutExpired:
        raise PartOpError(f"{what}: команда {cmd[0]} не ответила вовремя.")
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or "").strip().splitlines()
        tail = msg[-1] if msg else f"код {r.returncode}"
        raise PartOpError(f"{what}: {tail}")
    return r.stdout


def _settle() -> None:
    """udevadm settle — best-effort. Отсутствие udev не должно валить
    операцию: узлы разделов создаёт ядро через devtmpfs, а надёжность
    даёт _wait_dev() ниже, а не эта строка."""
    try:
        subprocess.run(["udevadm", "settle", "--timeout=10"],
                       capture_output=True, timeout=15, env=_ENV)
    except Exception:
        pass


def _wait_dev(path: str, tries: int = 40, delay: float = 0.25) -> bool:
    for _ in range(tries):
        if os.path.exists(path):
            return True
        time.sleep(delay)
    return False


def fresh(disk: str) -> tuple[dict, dict]:
    """Свежая карта + контекст + mounted. Читает РЕАЛЬНЫЙ диск всегда:
    в режиме стенда сюда просто не доходит (гейт отказывает раньше)."""
    m = diskmap.read_disk(disk)
    if not m.get("disk"):
        raise PartOpError(f"Не удалось прочитать таблицу разделов {disk}.")
    ctx = diskmap.build_context(m)
    diskmap.fill_mounted(m)
    return m, ctx


def _numbers(m: dict) -> set:
    return {i["number"] for i in m["items"] if i["kind"] == "part"}


def _by_number(m: dict, number: int):
    for i in m["items"]:
        if i["kind"] == "part" and i["number"] == number:
            return i
    return None


def align_range(start: int, end: int) -> tuple[int, int]:
    """Начало вверх до границы 1 МиБ, конец — вниз так, чтобы следующий
    байт тоже лёг на границу. Возвращает (start, end) включительно."""
    s = ((start + ALIGN - 1) // ALIGN) * ALIGN
    e = ((end + 1) // ALIGN) * ALIGN - 1
    return s, e


# ────────────────────────── операции ────────────────────────────

def create(disk: str, start: int, end: int, fs: str | None = None,
           esp: bool | None = None, name: str | None = None) -> str:
    """Создать раздел в СВОБОДНОМ блоке. Возвращает путь нового раздела.

    start/end — байты, включительно, как их отдаёт parted print free.
    fs — 'fat32' | 'ext4' | ... | None (раздел без файловой системы).
    esp — принудительно взвести/не взводить флаг esp; None = авто
          (взводим для FAT, иначе нет).

    Предусловия проверяются ЗАНОВО по свежей карте: проверка в GUI —
    для человека, проверка здесь — для диска. Первая может устареть.
    """
    _require(disk)
    fs_key = (fs or "").strip().lower()
    if fs_key and fs_key not in _MKFS:
        raise PartOpError(f"Файловая система «{fs}» не поддерживается.")

    s, e = align_range(int(start), int(end))
    if e - s + 1 < MIN_CREATE:
        raise PartOpError(
            f"После выравнивания остаётся {diskmap.human(max(0, e - s + 1))} — "
            f"слишком мало, нужно хотя бы {diskmap.human(MIN_CREATE)}.")

    before, _ctx = fresh(disk)
    hole = None
    for it in before["items"]:
        if it["kind"] == "free" and it["start"] <= s and it["end"] >= e:
            hole = it
            break
    if hole is None:
        raise PartOpError(
            "Выбранный участок больше не свободен — таблица разделов "
            "изменилась. Обнови карту диска и повтори.")

    old_numbers = _numbers(before)
    ptype = _PTYPE.get(fs_key, "ext4")
    # Bug 39: на msdos флаг esp не делает раздел загрузочным для UEFI
    # (msdos так и не грузится), зато diskmap опознаёт его как
    # «Загрузчик EFI» и запрещает удаление — пользователь запирает
    # сам себя. Автоматически ставим esp ТОЛЬКО на GPT.
    # Явный esp=True от вызывающего уважаем как осознанный выбор.
    _table = (before["disk"].get("table") or "").lower()
    if esp is None:
        want_esp = diskmap.is_fat(fs_key) and _table not in ("msdos", "mbr")
    else:
        want_esp = bool(esp)
    parg = _part_arg(before["disk"].get("table"), fs_key, want_esp, name)
    _run(["parted", "-s", "-a", "optimal", disk, "mkpart",
          parg, ptype, f"{s}B", f"{e}B"],
         "Создание раздела")
    _settle()

    after, _ = fresh(disk)
    new = _numbers(after) - old_numbers
    if len(new) != 1:
        raise PartOpError(
            "Раздел создан, но опознать его не удалось: в таблице "
            f"появилось разделов — {len(new)}. Проверьте разделы вручную.")
    number = new.pop()
    item = _by_number(after, number)
    path = item["path"]

    if not _wait_dev(path):
        raise PartOpError(
            f"Раздел {path} создан, но устройство не появилось в системе. "
            "Возможно, диск занят. Перезагрузка live-среды обычно помогает.")

    if want_esp:
        # Без флага esp прошивка UEFI раздел не увидит (п. 10.3).
        _run(["parted", "-s", disk, "set", str(number), "esp", "on"],
             "Установка флага EFI")
        _settle()

    if fs_key:
        # ★ ДО перечитывания карты для показа: иначе флаг msftdata,
        #   который parted вешает сам, покажет раздел как «Windows».
        _run(_MKFS[fs_key] + [path], f"Создание файловой системы {fs_key}",
             timeout=600)
        _settle()

    return path


def mklabel(disk: str, table: str) -> str:
    """Bug 42. Создать таблицу разделов на диске, где её НЕТ.

    ★ Bug 46: метка "loop" — это НЕ таблица разделов, а признак того, что
    файловая система записана прямо на устройство. Считать её живой
    таблицей нельзя: тогда разметить такой диск станет нечем. Создавать
    таблицу здесь МОЖНО, но данные на этой ФС гибнут — предупреждение
    обязательно на стороне GUI (Bug 45).

    Сознательно НЕ умеет перезаписывать существующую таблицу: mklabel
    поверх живой метки — это молчаливое уничтожение всех разделов, и
    такой кнопки в установщике для новичков быть не должно. Если метка
    уже есть — отказ с объяснением.
    """
    _require(disk)
    if table not in ("gpt", "msdos"):
        raise PartOpError(f"Неизвестный тип таблицы разделов: {table}.")
    m = diskmap.read_disk(disk)
    cur = (m.get("disk") or {}).get("table", "")
    # Bug 46: "loop" приравнен к отсутствию таблицы — см. docstring.
    if cur and cur not in ("unknown", "loop"):
        raise PartOpError(
            f"На {disk} уже есть таблица разделов ({cur}). "
            f"Создание новой стёрло бы все разделы — операция отменена."
        )
    _run(["parted", "-s", disk, "mklabel", table],
         "Создание таблицы разделов")
    _settle()
    return f"{disk}: создана таблица разделов {table}."


def delete(disk: str, number: int) -> str:
    """Удалить раздел по номеру. Возвращает описание удалённого —
    для лога и для экрана подтверждения (уровень 3)."""
    _require(disk)
    m, ctx = fresh(disk)
    item = _by_number(m, int(number))
    if item is None:
        raise PartOpError(
            f"Раздела №{number} на диске больше нет — таблица изменилась. "
            "Обнови карту диска.")

    ok, why = diskmap.can_delete(item, ctx)
    if not ok:
        raise PartOpError(f"Этот раздел удалять нельзя: {why}.")

    label = (f"{item['path']} — {diskmap.human(item['size'])}, "
             f"{diskmap.describe(item, ctx)}")
    _run(["parted", "-s", disk, "rm", str(int(number))], "Удаление раздела")
    _settle()

    check, _ = fresh(disk)
    if _by_number(check, int(number)) is not None:
        raise PartOpError(
            f"parted отчитался об удалении, но раздел №{number} всё ещё "
            "в таблице. Ничего не изменилось, повтори позже.")
    return label
