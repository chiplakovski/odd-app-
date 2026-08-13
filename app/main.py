"""GUI entry point."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .config import APP_TITLE
from .ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("ODD")
    window = MainWindow()
    window.show()
    window.maximize_to_screen()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
