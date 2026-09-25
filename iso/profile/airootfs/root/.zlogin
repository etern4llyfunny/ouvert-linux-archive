# fix for screen readers
if grep -Fqa 'accessibility=' /proc/cmdline &> /dev/null; then
    setopt SINGLE_LINE_ZLE
fi

~/.automated_script.sh
# Установщик: tty1 запускает сам, с любого входа root — набрать `ouvert` (Bug 27)
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
