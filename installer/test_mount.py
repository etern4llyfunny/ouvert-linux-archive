#!/usr/bin/env python3
"""
test_mount.py — проверка _has_windows_loader() из diskmap.py.

БЕЗОПАСНОСТЬ: работает ТОЛЬКО с временными файлами-образами в /tmp.
Реальные диски не читаются и не монтируются. Всё за собой убирает.

Требует root (монтирование) и mkfs.vfat (пакет dosfstools).
Запуск:  sudo python test_mount.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diskmap


def sh(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} -> {r.returncode}\n{r.stderr}")
    return r.stdout


def make_image(path, with_windows):
    sh("dd", "if=/dev/zero", f"of={path}", "bs=1M", "count=16", "status=none")
    sh("mkfs.vfat", "-F", "16", path)
    tmp = tempfile.mkdtemp(prefix="mkimg-")
    try:
        sh("mount", path, tmp)
        if with_windows:
            d = os.path.join(tmp, "EFI", "Microsoft", "Boot")
            os.makedirs(d)
            with open(os.path.join(d, "bootmgfw.efi"), "wb") as f:
                f.write(b"\0" * 4096)
        else:
            os.makedirs(os.path.join(tmp, "EFI", "Ouvert Linux"))
    finally:
        subprocess.run(["umount", tmp], capture_output=True)
        os.rmdir(tmp)


def main():
    if os.geteuid() != 0:
        print("нужен root: sudo python test_mount.py")
        return 1
    if not shutil.which("mkfs.vfat"):
        print("нет mkfs.vfat — поставь dosfstools")
        return 1

    work = tempfile.mkdtemp(prefix="ouvert-test-")
    win = os.path.join(work, "esp_windows.img")
    ours = os.path.join(work, "esp_ours.img")
    broken = os.path.join(work, "esp_broken.img")
    ok = True
    try:
        make_image(win, True)
        make_image(ours, False)
        # битый образ: не ФС вообще -> смонтировать нельзя
        sh("dd", "if=/dev/urandom", f"of={broken}", "bs=1M", "count=4", "status=none")

        cases = [
            ("ESP с загрузчиком Windows", win, True),
            ("наш ESP, винды нет", ours, False),
            ("битый раздел (проверить нельзя)", broken, None),
            ("несуществующее устройство", "/dev/does-not-exist-zz", None),
        ]
        for title, dev, expect in cases:
            got = diskmap._has_windows_loader(dev)
            good = got is expect
            ok &= good
            print(f"[{'OK ' if good else 'ПРОВАЛ'}] {title:<34} ждали {expect!s:<5} получили {got!s}")

        print()
        print("ИТОГ:", "все ветки работают" if ok else "ЕСТЬ ПРОВАЛЫ")

        left = subprocess.run(["findmnt", "-rno", "TARGET"], capture_output=True, text=True).stdout
        stray = [l for l in left.splitlines() if "ouvert-esp-" in l]
        print("подвисших точек монтирования:", len(stray))
        ok &= not stray
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
