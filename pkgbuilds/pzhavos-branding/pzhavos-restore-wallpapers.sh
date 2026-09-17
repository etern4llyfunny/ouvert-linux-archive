#!/bin/bash
# PzhavOS: восстановление обоев после обновления пакетов, которые их перетирают
# (xfdesktop, plasma-workspace-wallpapers и любые их наследники).
# Вызывается хуком /usr/share/libalpm/hooks/pzhavos-wallpapers.hook.
# Повторяет логику установщика (config_gen.py, блок обоев).
#
# ПРИНЦИП: никогда не валить транзакцию pacman. Нет set -e, всегда exit 0.

SRC_XFCE=/usr/share/wallpapers/PzhavOS/pzhav.png
SRC_KDE=/usr/share/wallpapers/PzhavOS/pzhav-kde.png

# XFCE: подмена дефолтных фонов xfdesktop. GdkPixbuf определяет формат по
# содержимому, поэтому PNG под именем *.svg рендерится нормально.
if [ -f "$SRC_XFCE" ] && [ -d /usr/share/backgrounds/xfce ]; then
  for f in /usr/share/backgrounds/xfce/*; do
    [ -f "$f" ] || continue
    cmp -s "$SRC_XFCE" "$f" || cp -f "$SRC_XFCE" "$f" || true
  done
fi

# KDE Plasma: подмена содержимого дефолтного набора Next, все разрешения
# + images_dark.
if [ -f "$SRC_KDE" ] && [ -d /usr/share/wallpapers/Next/contents ]; then
  for f in /usr/share/wallpapers/Next/contents/images/*.png \
           /usr/share/wallpapers/Next/contents/images_dark/*.png; do
    [ -f "$f" ] || continue
    cmp -s "$SRC_KDE" "$f" || cp -f "$SRC_KDE" "$f" || true
  done
fi

exit 0
