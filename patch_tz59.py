#!/usr/bin/env python3
"""Патч 59 — осознанный выбор часового пояса + цвет предупреждения из темы.

1. i18n.py: три новых ключа (регион/город/ошибка) в обоих языках.
2. pages.py, TimezonePage: вместо предвыбранного Europe/Moscow —
   плейсхолдеры «Выберите регион/город», город заблокирован до выбора
   региона, появился метод validate().
3. wizard.py, go(): общий хук — перед переходом вперёд страница, у которой
   есть validate(), проверяет себя сама.
4. pages.py, DiskPage: цвет предупреждения #c67573 (старый бренд) заменён
   на objectName("warning") — цвет теперь живёт в теме.

Запуск:
    python3 patch_tz59.py --dry
    python3 patch_tz59.py
"""
import ast
import shutil
import sys
import time
from pathlib import Path

ROOT = Path.home() / "pzhavos"
DRY = "--dry" in sys.argv
STAMP = time.strftime("%Y%m%d-%H%M%S")
COPIES = ["installer", "iso/profile/airootfs/opt/ouvert-installer"]

I18N_OLD = '    "tz_city": {"ru": "Город", "en": "City"},\n'
I18N_NEW = I18N_OLD + (
    '    "tz_pick_region": {"ru": "Выберите регион", "en": "Select region"},\n'
    '    "tz_pick_city": {"ru": "Выберите город", "en": "Select city"},\n'
    '    "err_no_tz": {"ru": "Выбери регион и город.", "en": "Select region and city."},\n'
)

TZ_INIT_OLD = '''        tz = self.state.get("timezone") or "Europe/Moscow"
        region, _, city = tz.partition("/")
        if region in self.regions:
            self.region_combo.setCurrentText(region)
            self._fill_cities(region)
            if city in self.regions[region]:
                self.city_combo.setCurrentText(city)
        self.retranslate()
'''
TZ_INIT_NEW = '''        # ничего не выбрано заранее: пояс выбирают осознанно
        self.region_combo.setCurrentIndex(-1)
        self.city_combo.setEnabled(False)
        tz = self.state.get("timezone") or ""
        region, _, city = tz.partition("/")
        if region in self.regions:
            self.region_combo.setCurrentText(region)
            if city in self.regions[region]:
                self.city_combo.setCurrentText(city)
        self.retranslate()
'''

FILL_OLD = '''    def _fill_cities(self, region: str) -> None:
        self.city_combo.clear()
        self.city_combo.addItems(self.regions.get(region, []))
'''
FILL_NEW = '''    def _fill_cities(self, region: str) -> None:
        self.city_combo.clear()
        self.city_combo.addItems(self.regions.get(region, []))
        self.city_combo.setCurrentIndex(-1)
        self.city_combo.setEnabled(bool(region))
        self.state.pop("timezone", None)
'''

RETR_OLD = '''    def retranslate(self) -> None:
        self.title.setText(tr("tz_title"))
        self.l_region.setText(tr("tz_region"))
        self.l_city.setText(tr("tz_city"))
'''
RETR_NEW = '''    def validate(self) -> str | None:
        if not self.state.get("timezone"):
            return tr("err_no_tz")
        return None

    def retranslate(self) -> None:
        self.title.setText(tr("tz_title"))
        self.l_region.setText(tr("tz_region"))
        self.l_city.setText(tr("tz_city"))
        self.region_combo.setPlaceholderText(tr("tz_pick_region"))
        self.city_combo.setPlaceholderText(tr("tz_pick_city"))
'''

WARN_OLD = '        self.warn.setStyleSheet("color: #c67573; font-weight: 600;")\n'
WARN_NEW = '        self.warn.setObjectName("warning")\n'

GO_OLD = '''        if delta > 0:
            page = self.pages[i]
            if page is self.net_page and not self.state.get("net_ok"):
'''
GO_NEW = '''        if delta > 0:
            page = self.pages[i]
            if (check := getattr(page, "validate", None)) and (err := check()):
                QMessageBox.warning(self, "Ouvert Linux", err)
                return
            if page is self.net_page and not self.state.get("net_ok"):
'''

# (маркер уже применённой правки, якорь, замена)
EDITS = {
    "i18n.py": [('"err_no_tz"', I18N_OLD, I18N_NEW)],
    "pages.py": [("ничего не выбрано заранее", TZ_INIT_OLD, TZ_INIT_NEW),
                 ("setEnabled(bool(region))", FILL_OLD, FILL_NEW),
                 ("def validate(self)", RETR_OLD, RETR_NEW),
                 ('setObjectName("warning")', WARN_OLD, WARN_NEW)],
    "wizard.py": [('getattr(page, "validate"', GO_OLD, GO_NEW)],
}


def main():
    plan, problems = [], []
    for base in COPIES:
        for fname, edits in EDITS.items():
            p = ROOT / base / fname
            if not p.is_file():
                problems.append(f"нет файла: {p}")
                continue
            src = p.read_text(encoding="utf-8")
            dst, applied, already = src, 0, 0
            for marker, old, new in edits:
                if marker in dst:
                    already += 1
                    continue
                n = dst.count(old)
                if n == 1:
                    dst = dst.replace(old, new, 1)
                    applied += 1
                else:
                    problems.append(f"{base}/{fname}: якорь найден {n} раз, ожидался 1\n"
                                    f"    {old.strip().splitlines()[0][:70]}")
            if dst != src:
                plan.append((f"{base}/{fname}", p, src, dst, applied, already))
            elif already:
                print(f"{base}/{fname}: уже применено ({already})")

    if problems:
        sys.exit("ПАТЧ НЕ ПРИМЕНЁН:\n  " + "\n  ".join(problems))

    print(f"{'ФАЙЛ':58} ПРАВОК  БЫЛО→СТАЛО")
    for rel, _, src, dst, applied, _ in plan:
        print(f"{rel:58} {applied:5}  {len(src.encode())}→{len(dst.encode())}")
    if not plan:
        print("Изменений нет.")

    if DRY:
        print("\nКОНТРОЛЬНЫЙ ПРОГОН: ничего не записано.")
        return

    for rel, p, _, dst, _, _ in plan:
        ast.parse(dst)  # сначала проверяем, потом пишем
    for rel, p, _, dst, _, _ in plan:
        shutil.copy2(p, p.with_name(p.name + f".p59bak-{STAMP}"))
        p.write_text(dst, encoding="utf-8")
    print(f"\nЗаписано файлов: {len(plan)}. Бэкапы: *.p59bak-{STAMP}")


if __name__ == "__main__":
    main()
