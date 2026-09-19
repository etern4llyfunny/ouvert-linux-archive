#!/usr/bin/env python3
"""
patch_bug18.py — заносит фикс Bug 18 в УСТАНОВЩИК (config_gen.py).

Bug 18: terminal_output gfxterm в BIOS на нашем ISO ломает передачу
управления GRUB -> ядру (чёрный экран, ядро не стартует). Лечение —
GRUB_TERMINAL_OUTPUT=console. Ручная правка /boot/grub/grub.cfg НЕ годится:
улетит при первом grub-mkconfig. Поэтому фикс кладём в /etc/default/grub,
чтобы он пережил перегенерацию.

Что делает скрипт: в build_custom_commands() config_gen.py, в критикал-блоке
ЭТАП 3, ВСТАВЛЯЕТ идемпотентную установку GRUB_TERMINAL_OUTPUT=console
ПЕРЕД строкой grub-mkconfig. Стиль — тот же, что у GRUB_BACKGROUND рядом
(grep активной строки -> sed на месте, иначе append в конец).

Свойства:
  * идемпотентный  — повторный запуск ничего не дублирует (маркер в тексте);
  * assert по якорям — падает, если структура файла не та (а не молча портит);
  * правит ОБЕ копии config_gen.py;
  * в конце гоняет py_compile обоих файлов.

Запуск (ХОСТ):
  python3 patch_bug18.py
"""
import subprocess
import sys

DEFAULT_PATHS = [
    "/home/admin/pzhavos/installer/config_gen.py",
    "/home/admin/pzhavos/iso/profile/airootfs/opt/pzhavos-installer/config_gen.py",
]

# Якорь вставки: строка с grub-mkconfig (без обратных слэшей -> надёжно ищется).
ANCHOR = "grub-mkconfig -o /boot/grub/grub.cfg"
# Контекст (sanity): мы точно в GRUB-блоке ЭТАП 3.
CONTEXT = "GRUB_BACKGROUND"
# Маркер идемпотентности.
MARKER = "GRUB_TERMINAL_OUTPUT"

# Вставляемые строки — ТОЧНО как они должны лечь в .py (отступ 8 пробелов).
# raw-строки: \n в конце последней строки должен остаться ЛИТЕРАЛЬНЫМ
# (это байты \ и n внутри строкового литерала самого config_gen.py).
# console без кавычек — одно слово, кавычки не нужны (идиома GRUB).
INSERT = [
    r'''        "grep -q '^GRUB_TERMINAL_OUTPUT=' /etc/default/grub"''',
    r'''        " && sed -i 's|^GRUB_TERMINAL_OUTPUT=.*|GRUB_TERMINAL_OUTPUT=console|' /etc/default/grub"''',
    r'''        " || echo 'GRUB_TERMINAL_OUTPUT=console' >> /etc/default/grub\n"''',
]


def patch_one(path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    if MARKER in text:
        print(f"SKIP  (уже пропатчен): {path}")
        return

    assert CONTEXT in text, f"НЕТ якоря контекста {CONTEXT!r}: {path}"

    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ANCHOR in ln]
    assert len(hits) == 1, f"якорь {ANCHOR!r} встретился {len(hits)} раз (ждали 1): {path}"

    i = hits[0]
    assert any(CONTEXT in ln for ln in lines[:i]), \
        f"{CONTEXT!r} не найден ПЕРЕД якорём — вставка не туда: {path}"

    new_lines = lines[:i] + INSERT + lines[i:]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))

    # Пост-проверка: маркер появился и стоит ПЕРЕД grub-mkconfig.
    after = open(path, encoding="utf-8").read().split("\n")
    mi = next(k for k, ln in enumerate(after) if MARKER in ln)
    gi = next(k for k, ln in enumerate(after) if ANCHOR in ln)
    assert mi < gi, f"пост-проверка: маркер оказался после grub-mkconfig: {path}"
    print(f"OK    пропатчен: {path}")


def main(paths):
    for p in paths:
        patch_one(p)
    for p in paths:
        subprocess.run([sys.executable, "-m", "py_compile", p], check=True)
    print("py_compile OK для всех файлов.")


if __name__ == "__main__":
    main(DEFAULT_PATHS)
