"""Профили archinstall 4.4: (показ, имя профиля archinstall, greeter)."""

DESKTOP_ENVIRONMENTS = [
    ("KDE Plasma", "KDE Plasma", "plasma-login-manager"),
    ("GNOME", "GNOME", "gdm"),
    ("Cinnamon", "Cinnamon", "lightdm-gtk-greeter"),
    ("XFCE", "Xfce4", "lightdm-gtk-greeter"),
    ("MATE", "Mate", "lightdm-gtk-greeter"),
    ("Budgie", "Budgie", "lightdm-slick-greeter"),
    ("LXQt", "Lxqt", "sddm"),
    ("Deepin", "Deepin", "lightdm-gtk-greeter"),
    ("Enlightenment", "Enlightenment", "lightdm-gtk-greeter"),
    ("COSMIC", "Cosmic", "cosmic-greeter"),
]

WINDOW_MANAGERS = [
    ("Hyprland", "Hyprland", "sddm"),
    ("Niri + DankMaterialShell", "niri - DankMaterialShell", "dms-greeter"),
    ("Niri", "niri", "lightdm-gtk-greeter"),
    ("Sway", "Sway", "lightdm-gtk-greeter"),
    ("i3", "i3-wm", "lightdm-gtk-greeter"),
    ("River", "River", "lightdm-gtk-greeter"),
    ("Labwc", "Labwc", "lightdm-gtk-greeter"),
    ("Awesome", "Awesome", "lightdm-gtk-greeter"),
    ("Bspwm", "Bspwm", "lightdm-gtk-greeter"),
    ("Qtile", "Qtile", "lightdm-gtk-greeter"),
    ("Xmonad", "Xmonad", "lightdm-gtk-greeter"),
]

# custom_settings, которые archinstall требует для некоторых WM
CUSTOM_SETTINGS = {
    "Hyprland": {"Hyprland": {"seat_access": "polkit"}},
    "Sway": {"Sway": {"seat_access": "polkit"}},
}
