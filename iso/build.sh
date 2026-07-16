#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# 1. Инсталлер
mkdir -p profile/airootfs/opt
rsync -a --delete --exclude __pycache__ ../installer/ profile/airootfs/opt/pzhavos-installer/

# 2. Репозиторий pzhavos.
# В живой системе он окажется как /opt/pzhavos-repo/x86_64 — ровно этот путь
# прописан в config_gen.REPO_DIR (file:///opt/pzhavos-repo/x86_64).
# --delete обязателен: иначе старые версии пакетов копятся в ISO.
# Каталог в .gitignore — пакеты уже лежат в git в repo/x86_64/, второй
# экземпляр на 140 МБ там не нужен.
mkdir -p profile/airootfs/opt/pzhavos-repo
rsync -a --delete --exclude '*.old' ../repo/x86_64/ profile/airootfs/opt/pzhavos-repo/x86_64/

echo "== Репо в ISO: =="
ls profile/airootfs/opt/pzhavos-repo/x86_64/ | grep -c 'pkg.tar.zst' | xargs echo "пакетов:"
du -sh profile/airootfs/opt/pzhavos-repo/

sudo rm -rf /tmp/archiso-work
sudo mkarchiso -v -w /tmp/archiso-work -o out profile
