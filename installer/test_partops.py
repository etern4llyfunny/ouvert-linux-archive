#!/usr/bin/env python3
"""Тест partops.py. Пишет НА САМОМ ДЕЛЕ, но только на loop-файл.

Запуск:  sudo python test_partops.py
Ничего, кроме собственного временного файла, не трогает.
"""
import os
import subprocess
import time
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diskmap
import partops

MiB = 1024 * 1024
GiB = 1024 * MiB

ok_n = fail_n = 0


def check(cond, name):
    global ok_n, fail_n
    if cond:
        ok_n += 1
        print(f"  ok   {name}")
    else:
        fail_n += 1
        print(f"  FAIL {name}")


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True,
                          env={"LC_ALL": "C", "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"})


def raises(fn, needle=""):
    try:
        fn()
    except partops.PartOpError as e:
        return needle.lower() in str(e).lower()
    except Exception:
        return False
    return False


# ═══════════════ ЧАСТЬ 1. ГЕЙТ (без диска) ═══════════════
print("\n[1] ГЕЙТ ЗАПИСИ")
for k in ("OUVERT_DISKMAP_SAMPLE", "OUVERT_PARTOPS_ALLOW"):
    os.environ.pop(k, None)

ok, why = partops.write_allowed("/dev/zzz")
check(not ok, "без archiso и без белого списка — запрет")
check("Ouvert Linux" in why, "текст отказа объясняет, что делать")

os.environ["OUVERT_DISKMAP_SAMPLE"] = "tests/sample_t26.txt"
os.environ["OUVERT_PARTOPS_ALLOW"] = "/dev/zzz"
ok, why = partops.write_allowed("/dev/zzz")
check(not ok, "★ стенд запрещает запись ДАЖЕ с белым списком")
check("стенд" in why.lower(), "отказ называет причиной стенд")
del os.environ["OUVERT_DISKMAP_SAMPLE"]

ok, _ = partops.write_allowed("/dev/zzz")
check(ok, "белый список разрешает названное устройство")
ok, why = partops.write_allowed("/dev/sda")
check(not ok, "★ белый список НЕ разрешает соседнее устройство")

real_euid = os.geteuid
os.geteuid = lambda: 1000
ok, why = partops.write_allowed("/dev/zzz")
os.geteuid = real_euid                       # ★ подменил — верни (урок 13.6)
check(not ok and "root" in why, "без root — запрет")
check(os.geteuid() == 0, "★ geteuid восстановлен в том же тесте")

check(raises(lambda: partops.create("/dev/sda", 0, GiB, "ext4"), "не входит"),
      "create на чужом устройстве отбит гейтом")

# ═══════════════ ЧАСТЬ 2. НАСТОЯЩАЯ ЗАПИСЬ ═══════════════
print("\n[2] ПОДГОТОВКА LOOP-СТЕНДА")
img = tempfile.mktemp(prefix="ouvert-partops-", suffix=".img")
sh(["truncate", "-s", "2G", img])
r = sh(["losetup", "-fP", "--show", img])
loop = r.stdout.strip()
check(loop.startswith("/dev/loop"), f"loop создан: {loop}")
if not loop:
    print("нет loop — дальше нельзя")
    sys.exit(1)
os.environ["OUVERT_PARTOPS_ALLOW"] = loop
sh(["parted", "-s", loop, "mklabel", "gpt"])
m, ctx = partops.fresh(loop)
check(m["disk"]["table"] == "gpt", "таблица GPT прочитана")

print("\n[3] CREATE — FAT32 + флаг esp")
free = [i for i in m["items"] if i["kind"] == "free"][0]
p1 = partops.create(loop, free["start"], free["start"] + 300 * MiB - 1, "fat32")
check(os.path.exists(p1), f"устройство {p1} появилось")
m, ctx = partops.fresh(loop)
it1 = [i for i in m["items"] if i.get("path") == p1][0]
check(it1["fstype"] == "fat32", f"ФС fat32 создана (parted видит {it1['fstype']})")
check("esp" in it1["flags"], f"★ флаг esp взведён: {it1['flags']}")
check(it1["start"] % MiB == 0, f"начало выровнено на 1 МиБ: {it1['start']}")
check(diskmap.describe(it1, ctx) == "Загрузчик EFI",
      f"описание: {diskmap.describe(it1, ctx)}")

print("\n[4] ★ ЛОВУШКА msftdata — В ТОЙ ФОРМЕ, В КАКОЙ ОНА РЕАЛЬНО ЕСТЬ")
free = [i for i in m["items"] if i["kind"] == "free" and i["size"] > 600 * MiB][0]
p_raw = partops.create(loop, free["start"], free["start"] + 200 * MiB - 1,
                       "fat32", esp=False)
m, ctx = partops.fresh(loop)
it_raw = [i for i in m["items"] if i.get("path") == p_raw][0]
print(f"       fat32 без esp: флаги={it_raw['flags']} → «{diskmap.describe(it_raw, ctx)}»")
check("msftdata" in it_raw["flags"],
      "★ parted вешает msftdata на fat32 — ловушка реальна")
check(diskmap.describe(it_raw, ctx) == "Раздел данных Windows",
      "★ FAT32 без esp выглядит как виндовый — вот зачем esp до mkfs")
check("primary" not in (it_raw["name"] or ""),
      f"★ имя раздела не «primary» на GPT (name={it_raw['name']!r})")
n_raw = it_raw["number"]

print("\n[5] CREATE — ext4, ловушка обезврежена")
free = [i for i in m["items"] if i["kind"] == "free" and i["size"] > 500 * MiB][0]
p2 = partops.create(loop, free["start"], free["start"] + 400 * MiB - 1, "ext4")
m, ctx = partops.fresh(loop)
it2 = [i for i in m["items"] if i.get("path") == p2][0]
check(it2["fstype"] == "ext4", f"ФС ext4 создана ({it2['fstype']})")
check("msftdata" not in it2["flags"],
      f"★ на ext4 parted msftdata НЕ вешает: {it2['flags']} — гипотеза была шире правды")
check(diskmap.describe(it2, ctx) == "Linux (ext4)",
      f"★ но описание верное: «{diskmap.describe(it2, ctx)}» — слой ФС перебил флаг")
check("esp" not in it2["flags"], "esp на ext4 НЕ взведён")

print("\n[6] ОТКАЗЫ CREATE")
check(raises(lambda: partops.create(loop, it2["start"], it2["end"], "ext4"),
             "больше не свободен"),
      "★ создание поверх существующего раздела запрещено")
free = [i for i in m["items"] if i["kind"] == "free"][-1]
check(raises(lambda: partops.create(loop, free["start"],
                                    free["start"] + 3 * MiB, "ext4"),
             "слишком мало"),
      "слишком маленький раздел отбит")
check(raises(lambda: partops.create(loop, free["start"],
                                    free["start"] + 100 * MiB, "reiserfs"),
             "не поддерживается"),
      "неизвестная ФС отбита ДО записи")

print("\n[7] DELETE")
n2 = it2["number"]
label = partops.delete(loop, n2)
check("Linux (ext4)" in label, f"описание удалённого: «{label}»")
m, ctx = partops.fresh(loop)
check(all(i.get("number") != n2 for i in m["items"] if i["kind"] == "part"),
      "раздел исчез из таблицы")
check(raises(lambda: partops.delete(loop, n2), "больше нет"),
      "повторное удаление отбито внятно")
check(raises(lambda: partops.delete(loop, 99), "больше нет"),
      "удаление несуществующего номера отбито")

print("\n[8] ★ ЗАЩИТА ЧУЖОГО (can_delete вызывается ПЕРЕД записью)")
sh(["parted", "-s", loop, "set", str(n_raw), "msftres", "on"])
m, ctx = partops.fresh(loop)
it_p = [i for i in m["items"] if i.get("number") == n_raw][0]
check("msftres" in it_p["flags"], f"флаг msftres поставлен: {it_p['flags']}")
check(raises(lambda: partops.delete(loop, n_raw), "служебный раздел windows"),
      "★ удаление MSR запрещено САМИМ МОДУЛЕМ, а не только GUI")
m, ctx = partops.fresh(loop)
check(any(i.get("number") == n_raw for i in m["items"] if i["kind"] == "part"),
      "★ раздел на месте — отказ произошёл ДО записи")

print("\n[9] ЕДИНСТВЕННЫЙ ESP")
m, ctx = partops.fresh(loop)
check(ctx["esp_count"] == 1, f"esp_count={ctx['esp_count']}")
n1 = [i for i in m["items"] if i.get("path") == p1][0]["number"]
why9 = ""
try:
    partops.delete(loop, n1)
except partops.PartOpError as e:
    why9 = str(e)
print(f"       причина отказа: {why9}")
check(bool(why9), "★ удаление EFI-раздела ЗАПРЕЩЕНО")
check(("единственный efi" in why9.lower()) or ("не удалось проверить" in why9.lower()),
      "причина — либо «единственный ESP», либо fail-closed при нечитаемом ESP")
m, ctx = partops.fresh(loop)
check(any(i.get("number") == n1 for i in m["items"] if i["kind"] == "part"),
      "★ ESP на месте — отказ произошёл ДО записи")

print("\n[10] УБОРКА")
sh(["losetup", "-d", loop])
os.path.exists(img) and os.unlink(img)
check(not os.path.exists(img), "временный файл удалён")
# losetup -d освобождает устройство НЕ мгновенно: ядро ждёт закрытия
# узлов разделов. Задержка микроскопическая, но проверка без ожидания
# ловит её стабильно. Опыт без монтирования ESP её НЕ воспроизводит.
for _ in range(20):
    if loop not in sh(["losetup", "-a"]).stdout:
        break
    time.sleep(0.1)
check(loop not in sh(["losetup", "-a"]).stdout, "loop отцеплен")

print(f"\n{'='*56}\nПРОВЕРОК: {ok_n + fail_n}   ok: {ok_n}   FAIL: {fail_n}\n{'='*56}")
sys.exit(1 if fail_n else 0)
