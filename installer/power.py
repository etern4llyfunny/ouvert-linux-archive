"""Патч 73: логотип «Орбита» — кнопка питания (морф в ⏻) и заставка.

Геометрия — из исходника логотипа (claude/Ouvert_логотип.txt): кольцо R=30
с разрывом −98°…−10°, хвост — лог-спираль 285°→350°, r: R→1.9R. Углы
экранные, y вниз. При t=1 разрыв стоит на −130°…−50°, хвост — вертикаль ⏻.
Те же формулы, что в прототипе 04.11 (780 мс, «пружинка»).
"""
import math
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import (
    QElapsedTimer, QEasingCurve, QPoint, QPointF, QRectF, Qt, QTimer, QVariantAnimation,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QWidget

from i18n import current_lang
from theme import C

R, N = 30.0, 48
DURATION = 780       # мс на полный морф
HOVER = 0.1          # при наведении хвост чуть тянется к центру: «я кнопка»
WAKE_DELAY = 600     # мс: случайный толчок мыши сразу после запуска не гасит заставку
MENU_DELAY = 250     # мс (Патч 73.1): меню после начала морфа, иначе в cage морф не виден

_EASE = QEasingCurve(QEasingCurve.Type.OutBack)
_EASE.setOvershoot(1.9)      # «пружинка»


def _ease(x: float) -> float:
    # Патч 73.2: сначала разгон (x²), отскок — в конце. Чистый OutBack делал
    # почти весь морф за первую треть и съедал половину ещё на наведении.
    x = min(1.0, max(0.0, x))
    return _EASE.valueForProgress(x * x)


def geometry(t: float) -> tuple[QPainterPath, QPainterPath]:
    """(кольцо, хвост) в единицах логотипа: t=0 — логотип, t=1 — ⏻."""
    e = _ease(t)
    s, f = -10 - 40 * e, 262 - 32 * e          # экранные градусы, по часовой
    box = QRectF(-R, -R, 2 * R, 2 * R)
    ring = QPainterPath()
    ring.arcMoveTo(box, -s)                     # у Qt углы против часовой
    ring.arcTo(box, -s, -(f - s))
    tail = QPainterPath()
    for i in range(N + 1):
        u = i / N
        k = _ease((t - .3 * u) / .7)            # конец хвоста отстаёт — сматывается
        th = math.radians(285 + 65 * u + (270 - 285 - 65 * u) * k)
        r0 = R * 1.9 ** u
        r = r0 + (36 - 30 * u - r0) * k
        p = QPointF(r * math.cos(th), r * math.sin(th))
        tail.moveTo(p) if i == 0 else tail.lineTo(p)
    return ring, tail


def _pen(color: str) -> QPen:
    return QPen(QColor(color), 8, Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)


def draw_logo(p: QPainter, ring: QPainterPath, tail: QPainterPath) -> None:
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(C["blue"]))
    p.drawPath(ring)
    p.setPen(_pen(C["coral"]))
    p.drawPath(tail)


class PowerLogo(QWidget):
    """Логотип в шапке. Клик — морф в ⏻ и меню; меню закрылось — обратно."""

    def __init__(self, menu, parent=None):
        super().__init__(parent)
        self.menu = menu
        self.t = 0.0
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Патч 73.1: фокус только с клавиатуры — от клика вокруг логотипа
        # рисовалась рамка фокуса, похожая на лишнюю орбиту
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._kbd = False
        self._opening = False
        self._hidden = QElapsedTimer()
        self._anim = QVariantAnimation(self)
        self._anim.valueChanged.connect(self._set)
        menu.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay)
        menu.aboutToHide.connect(self._closed)

    def _closed(self) -> None:
        self._hidden.start()
        self.go(HOVER if self.underMouse() else 0.0)

    def _set(self, v) -> None:
        self.t = float(v)
        self.update()

    def go(self, target: float) -> None:
        # Патч 73.3: setEndValue у остановленной анимации сразу шлёт
        # valueChanged(конец) и переписывал self.t — длительность выходила 1 мс.
        start = self.t
        self._anim.blockSignals(True)
        self._anim.stop()
        self._anim.setDuration(max(1, int(DURATION * abs(target - start))))
        self._anim.setStartValue(start)
        self._anim.setEndValue(float(target))
        self._anim.blockSignals(False)
        self._anim.start()

    def open_menu(self) -> None:
        # Патч 73.1: клик, закрывший меню, под Wayland доходит и до логотипа —
        # не открываем меню заново тем же кликом
        if self._opening or self.menu.isVisible():
            return
        if self._hidden.isValid() and self._hidden.elapsed() < 250:
            return
        self._opening = True
        self.go(1.0)
        QTimer.singleShot(MENU_DELAY, self._popup)

    def _popup(self) -> None:
        self._opening = False
        self.menu.popup(self.mapToGlobal(QPoint(0, self.height() + 6)))

    def enterEvent(self, e) -> None:
        if not self.menu.isVisible():
            self.go(HOVER)

    def leaveEvent(self, e) -> None:
        if not self.menu.isVisible():
            self.go(0.0)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.open_menu()

    def keyPressEvent(self, e) -> None:
        if e.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.open_menu()
        else:
            super().keyPressEvent(e)

    def focusInEvent(self, e) -> None:
        self._kbd = e.reason() in (Qt.FocusReason.TabFocusReason,
                                   Qt.FocusReason.BacktabFocusReason)
        super().focusInEvent(e)
        self.update()

    def focusOutEvent(self, e) -> None:
        self._kbd = False
        super().focusOutEvent(e)
        self.update()

    def paintEvent(self, e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.hasFocus() and self._kbd:
            p.setPen(QPen(QColor(C["blue"]), 1.5))
            p.drawEllipse(QRectF(self.rect()).adjusted(1, 1, -1, -1))
        k = min(self.width(), self.height()) / 100.13     # viewBox логотипа
        p.scale(k, k)
        p.translate(37, 50.13)
        draw_logo(p, *geometry(self.t))


MONTHS = {
    "ru": ("января", "февраля", "марта", "апреля", "мая", "июня", "июля",
           "августа", "сентября", "октября", "ноября", "декабря"),
    "en": ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"),
}
DAYS = {
    "ru": ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"),
    "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
}


def clock_text(now: datetime, lang: str, zone: str) -> tuple[str, str]:
    """Без локалей: в live их может не быть, а месяц нужен в родительном падеже."""
    m, d = MONTHS.get(lang, MONTHS["en"])[now.month - 1], DAYS.get(lang, DAYS["en"])[now.weekday()]
    date = (f"{d}, {now.day} {m} {now.year}" if lang == "ru"
            else f"{d}, {m} {now.day}, {now.year}")
    return now.strftime("%H:%M:%S"), f"{date} · {zone}"


class Screensaver(QWidget):
    """Заставка поверх всего окна: логотипы отскакивают от краёв и друг от
    друга, каждый со своей постоянной скоростью; в углу часы. Любое движение
    мыши или клавиша — выход. Сталкиваются кольцами (хвосты могут пересекаться)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.hide()
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.stars: list[dict] = []
        self.zone, self.tz = "UTC", ZoneInfo("UTC")
        self.shift, self._minute, self._armed = QPoint(), -1, False
        self._prev = None           # Патч 73.4: у кого был фокус до заставки
        self._ring, self._tail = geometry(0.0)
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    # --- жизнь ---
    def start(self, zone: str | None) -> None:
        try:
            self.zone, self.tz = zone or "UTC", ZoneInfo(zone or "UTC")
        except Exception:
            self.zone, self.tz = "UTC", ZoneInfo("UTC")
        self.setGeometry(self.parentWidget().rect())
        self.stars, self._armed = [], False
        self._prev = QApplication.focusWidget()
        QTimer.singleShot(WAKE_DELAY, self._arm)
        self.show()
        self.raise_()
        self.setFocus()
        self._clock.start()
        self._timer.start()
        self._tick()

    def _arm(self) -> None:
        self._armed = True

    def _wake(self) -> None:
        if self._armed:
            self._timer.stop()
            # Патч 73.4: вернуть фокус, где был; иначе hide() отдаёт его
            # следующему «по Tab» — логотипу, и вокруг него рисуется кольцо
            try:
                back = self._prev is not None and self._prev.isVisible()
            except RuntimeError:        # виджет успели удалить
                back = False
            if back:
                self._prev.setFocus(Qt.FocusReason.OtherFocusReason)
            else:
                self.clearFocus()
            self.hide()

    def mouseMoveEvent(self, e) -> None:
        self._wake()

    def mousePressEvent(self, e) -> None:
        self._wake()

    def wheelEvent(self, e) -> None:
        self._wake()

    def keyPressEvent(self, e) -> None:
        self._wake()

    # --- физика (как в прототипе) ---
    def seed(self, w: int, h: int) -> None:
        n = round(min(18, max(8, w * h / 60000)))
        self.stars = []
        for _ in range(n):
            s = 36 + random.random() * 130
            r, a, v = .34 * s, random.random() * 2 * math.pi, 6 + s * .16
            for _try in range(80):       # без нахлёста, иначе слипнутся с первого кадра
                x = r + random.random() * max(1, w - 2 * r)
                y = r + random.random() * max(1, h - 2 * r)
                if all(math.hypot(q["x"] - x, q["y"] - y) >= q["r"] + r + 6 for q in self.stars):
                    break
            self.stars.append(dict(x=x, y=y, s=s, r=r, vx=math.cos(a) * v, vy=math.sin(a) * v,
                                   rot=random.random() * 360, vr=(random.random() - .5) * 14,
                                   al=.1 + .45 * (s - 36) / 130))
        self.stars.sort(key=lambda q: q["s"])

    def step(self, dt: float, w: int, h: int) -> None:
        for p in self.stars:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["rot"] += p["vr"] * dt
            if p["x"] < p["r"]:
                p["x"], p["vx"] = p["r"], abs(p["vx"])
            elif p["x"] > w - p["r"]:
                p["x"], p["vx"] = w - p["r"], -abs(p["vx"])
            if p["y"] < p["r"]:
                p["y"], p["vy"] = p["r"], abs(p["vy"])
            elif p["y"] > h - p["r"]:
                p["y"], p["vy"] = h - p["r"], -abs(p["vy"])
        # ponytail: O(n²) по парам — при n ≤ 18 это 153 проверки на кадр
        for i, a in enumerate(self.stars):
            for b in self.stars[i + 1:]:
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                d, lim = math.hypot(dx, dy), a["r"] + b["r"] - 1   # нахлёст ~1 px: «еле коснулись»
                if d >= lim or d == 0:
                    continue
                nx, ny, push = dx / d, dy / d, (lim - d) / 2
                a["x"] -= nx * push
                a["y"] -= ny * push
                b["x"] += nx * push
                b["y"] += ny * push
                # отражение от нормали касания: модуль скорости у каждого свой и не меняется
                for q, sign in ((a, 1), (b, -1)):
                    vn = (q["vx"] * nx + q["vy"] * ny) * sign
                    if vn > 0:
                        q["vx"] -= 2 * vn * nx * sign
                        q["vy"] -= 2 * vn * ny * sign

    def _tick(self) -> None:
        dt = min(.05, self._clock.restart() / 1000)
        area = self.parentWidget().rect()
        if self.geometry() != area:              # окно поменяло размер — пересеять
            self.setGeometry(area)
            self.stars = []
        if not self.stars:
            self.seed(self.width(), self.height())
        self.step(dt, self.width(), self.height())
        self.update()

    # --- картинка ---
    def paintEvent(self, e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#06090E"))
        for s in self.stars:
            p.save()
            p.translate(s["x"], s["y"])
            p.rotate(s["rot"])
            p.scale(s["s"] / 100, s["s"] / 100)
            p.setOpacity(s["al"])
            draw_logo(p, self._ring, self._tail)
            p.restore()

        now = datetime.now(self.tz)
        if now.minute != self._minute:           # раз в минуту сдвиг на пару пикселей: OLED
            self._minute = now.minute
            self.shift = QPoint(random.randint(-10, 10), random.randint(-8, 8))
        clock, date = clock_text(now, current_lang(), self.zone)
        box = self.rect().adjusted(28, 22, -28, -22).translated(self.shift)
        right_bottom = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom

        f = QFont(self.font())
        f.setPixelSize(max(13, self.height() // 60))
        p.setFont(f)
        p.setPen(QColor("#6F7C90"))
        p.drawText(box, right_bottom, date)
        lift = p.fontMetrics().height() + 6

        f.setPixelSize(max(32, self.height() // 14))
        f.setWeight(QFont.Weight.DemiBold)
        try:
            f.setFeature(QFont.Tag("tnum"), 1)  # цифры одной ширины: секунды не дрожат
        except AttributeError:
            pass
        p.setFont(f)
        p.setPen(QColor("#CFD8E6"))
        p.drawText(box.adjusted(0, 0, 0, -lift), right_bottom, clock)
