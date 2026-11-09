#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# 1. Инсталлер
mkdir -p profile/airootfs/opt
# Патч 71: без --delete-excluded исключённое (патчеры, тесты), раз попав
# в копию, оттуда уже не вычищается — --delete его не трогает
rsync -a --delete --delete-excluded --exclude __pycache__ --exclude '*.py.*' --exclude tests --exclude 'test_*.py' --exclude 'patch_*.py' --exclude stand_gui.py ../installer/ profile/airootfs/opt/ouvert-installer/

# 2. Репозиторий ouvert.
# В живой системе он окажется как /opt/ouvert-repo/x86_64 — ровно этот путь
# прописан в config_gen.REPO_DIR (file:///opt/ouvert-repo/x86_64).
# --delete обязателен: иначе старые версии пакетов копятся в ISO.
# Каталог в .gitignore — пакеты уже лежат в git в repo/x86_64/, второй
# экземпляр на 140 МБ там не нужен.
mkdir -p profile/airootfs/opt/ouvert-repo
rsync -a --delete --exclude '*.old' ../repo/x86_64/ profile/airootfs/opt/ouvert-repo/x86_64/

echo "== Репо в ISO: =="
ls profile/airootfs/opt/ouvert-repo/x86_64/ | grep -c 'pkg.tar.zst' | xargs echo "пакетов:"
du -sh profile/airootfs/opt/ouvert-repo/

sudo rm -rf /tmp/archiso-work
sudo mkarchiso -v -w /tmp/archiso-work -o out profile
