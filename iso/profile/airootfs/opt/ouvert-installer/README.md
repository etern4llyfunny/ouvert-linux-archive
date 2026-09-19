# Ouvert Linux Installer (каркас, Этап 1)

PySide6-фронтенд. Логика archinstall подключается позже как библиотека.

## Запуск для разработки (ХОСТ)
    cd ~/ouvert/installer
    python main.py

## Структура
- main.py     — точка входа
- wizard.py   — окно, шапка, навигация
- pages.py    — страницы (welcome/network/disk/user/desktop/summary)
- desktops.py — 21 профиль DE/WM из archinstall 4.4
- i18n.py     — переводы ru/en, переключение на лету
- theme.py    — тёмная тема, цвета бренда
- assets/     — лого

## Статус страниц
- Welcome, User, Desktop, Summary — рабочие
- Network (Wi-Fi), Disk, сам процесс установки — заглушки
