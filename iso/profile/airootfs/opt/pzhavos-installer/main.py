#!/usr/bin/env python3
"""PzhavOS Installer — точка входа."""
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from theme import apply_theme
from wizard import InstallerWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PzhavOS Installer")
    apply_theme(app)

    win = InstallerWindow()
    win.resize(920, 640)
    win.show()

    if "--smoke-test" in sys.argv:
        QTimer.singleShot(300, app.quit)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
