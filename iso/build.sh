#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p profile/airootfs/opt
rsync -a --delete --exclude __pycache__ ../installer/ profile/airootfs/opt/pzhavos-installer/
sudo rm -rf /tmp/archiso-work
sudo mkarchiso -v -w /tmp/archiso-work -o out profile
