"""GUI entry point."""
from __future__ import annotations

import sys

from PySide6.QtCore import QSharedMemory
from PySide6.QtWidgets import QApplication

from .config import APP_TITLE
from .ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("ODD")
    app.setQuitOnLastWindowClosed(False)

    # Refuse a second launch instead of running two Print Inbox watchers side by side -
    # kept alive as a local for the app's whole lifetime (released when main() returns).
    single_instance_lock = QSharedMemory("ODD-Inspection-Report-Generator-single-instance")
    if single_instance_lock.attach() or not single_instance_lock.create(1):
        return 0

    window = MainWindow()
    if "--tray" not in sys.argv[1:]:
        window.show()
        window.maximize_to_screen()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
