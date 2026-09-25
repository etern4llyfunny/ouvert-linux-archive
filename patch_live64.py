#!/usr/bin/env python3
"""Патч 64 — live-среда ISO, beta-4.

  • хвост Bug 27: motd советовал `python … main.py --live` без cage.
    Запуск установщика вынесен в zsh-функцию `ouvert` в /root/.zlogin:
    tty1 зовёт её сам, с любого другого входа root — набрать `ouvert`.
    motd теперь советует `ouvert`.
  • Bug 64: бэкапы патчей (*bak*) внутри airootfs уезжали в ISO — git rm.
  • iso_version beta-3 → beta-4.

Требует чистого git по трём файлам (бэкап = git). Идемпотентный.
Запуск: python ~/pzhavos/patch_live64.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path.home() / "pzhavos"
PROFILE = ROOT / "iso/profile"
AIROOTFS = PROFILE / "airootfs"

OLD_Z = """if [[ $(tty) == /dev/tty1 ]]; then
  cage -s -- env QT_QPA_PLATFORM=wayland python /opt/ouvert-installer/main.py --live
  if [[ $? -ne 0 ]]; then
    echo ''
    echo '>>> Ouvert Linux: GPU renderer failed. Restarting installer in software mode (pixman)...'
    sleep 3
    exec env WLR_RENDERER=pixman LIBGL_ALWAYS_SOFTWARE=1 cage -s -- env QT_QPA_PLATFORM=wayland WLR_RENDERER=pixman python /opt/ouvert-installer/main.py --live
  fi
fi
"""
NEW_Z = """# Установщик: tty1 запускает сам, с любого входа root — набрать `ouvert` (Bug 27)
ouvert() {
  cage -s -- env QT_QPA_PLATFORM=wayland python /opt/ouvert-installer/main.py --live && return
  echo ''
  echo '>>> Ouvert Linux: GPU renderer failed. Restarting installer in software mode (pixman)...'
  sleep 3
  env WLR_RENDERER=pixman LIBGL_ALWAYS_SOFTWARE=1 cage -s -- env QT_QPA_PLATFORM=wayland WLR_RENDERER=pixman python /opt/ouvert-installer/main.py --live
}
if [[ $(tty) == /dev/tty1 ]]; then
  ouvert
fi
"""

# (файл, старое, новое) — старое должно встречаться ровно 1 раз
EDITS = [
    (AIROOTFS / "root/.zlogin", OLD_Z, NEW_Z),
    (AIROOTFS / "etc/motd",
     "python /opt/ouvert-installer/main.py --live", "ouvert"),
    (PROFILE / "profiledef.sh", 'iso_version="beta-3"', 'iso_version="beta-4"'),
]


def git(*args, check=True):
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True, check=check).stdout


def die(msg):
    print(f"СТОП: {msg}\nНичего не записано.")
    sys.exit(1)


def rel(p):
    return str(p.relative_to(ROOT))


def main():
    if not (PROFILE / "profiledef.sh").is_file():
        die(f"нет {PROFILE}/profiledef.sh")

    # ── проход 1: только чтение и проверки ─────────────────────────────
    todo = []
    for path, old, new in EDITS:
        text = path.read_bytes().decode("utf-8")
        n_old, n_new = text.count(old), text.count(new)
        if n_old == 1:
            todo.append((path, text, text.replace(old, new)))
            print(f"  к правке:   {rel(path)}")
        elif n_old == 0 and n_new >= 1:
            print(f"  уже готово: {rel(path)}")
        else:
            die(f"{rel(path)}: якорь найден {n_old} раз (нужно 1), новый текст {n_new} раз")

    baks = sorted(p for p in AIROOTFS.rglob("*bak*") if p.is_file())
    tracked = set(git("ls-files", "--", *map(rel, baks)).split()) if baks else set()
    to_rm = [p for p in baks if rel(p) in tracked]
    for p in baks:
        print(f"  бэкап в airootfs: {rel(p)}  "
              f"{'→ git rm' if p in to_rm else '(НЕ в git — не трогаю, реши сам)'}")

    if not todo and not to_rm:
        print("Патч 64 уже применён.")
        return

    dirty = git("status", "--porcelain", "--", *(rel(p) for p, _, _ in todo))
    if dirty:
        die(f"незакоммиченные изменения:\n{dirty}")

    # ── проход 2: запись ───────────────────────────────────────────────
    for path, before, after in todo:
        path.write_bytes(after.encode("utf-8"))
        print(f"  {rel(path)}: {len(before.encode())} → {len(after.encode())} Б")

    zlogin = AIROOTFS / "root/.zlogin"
    if shutil.which("zsh"):
        r = subprocess.run(["zsh", "-n", str(zlogin)], capture_output=True, text=True)
        if r.returncode:
            git("checkout", "HEAD", "--", *(rel(p) for p, _, _ in todo))
            print(f"СТОП: zsh -n не прошёл, файлы откачены:\n{r.stderr}")
            sys.exit(1)
        print("  zsh -n .zlogin: OK")
    else:
        print("  zsh на хосте нет — синтаксис .zlogin проверится в live")

    for p in to_rm:
        git("rm", "-q", "--", rel(p))
        print(f"  git rm: {rel(p)}")

    left = git("grep", "-n", "beta-3", "--", "iso/profile", "installer", check=False)
    print("  'beta-3' в iso/profile и installer: " + (f"ОСТАЛОСЬ:\n{left}" if left else "нет"))

    paths = " ".join(rel(p) for p, _, _ in todo) + "".join(f" {rel(p)}" for p in to_rm)
    print(f"\nПатч 64 применён.\nОткат: git -C ~/pzhavos checkout HEAD -- {paths}")


if __name__ == "__main__":
    main()
