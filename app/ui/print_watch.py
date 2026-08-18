"""Watches the "oddprint" inbox folder and reports PDFs once they're fully written.

The oddprint virtual printer (see packaging/) drops one PDF per print job into
config.PRINT_INBOX_DIR with no further signal that the write is complete, so this polls
each newly-seen file's size until it stops changing before reporting it as ready.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QObject, QTimer, Signal

from ..config import PRINT_INBOX_DIR

_POLL_INTERVAL_MS = 700


class PrintInboxWatcher(QObject):
    fileReady = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        PRINT_INBOX_DIR.mkdir(parents=True, exist_ok=True)
        self._watcher = QFileSystemWatcher([str(PRINT_INBOX_DIR)], self)
        self._watcher.directoryChanged.connect(self._scan)
        self._pending: dict[str, int] = {}
        self._emitted: set[str] = set()
        self._timer = QTimer(self)
        self._timer.setInterval(_POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._check_pending)

    def scan_existing(self) -> None:
        """Pick up any PDFs already sitting in the inbox (e.g. printed while the app was closed)."""
        self._scan(str(PRINT_INBOX_DIR))

    def _scan(self, _path: str) -> None:
        for pdf in PRINT_INBOX_DIR.glob("*.pdf"):
            key = str(pdf)
            if key in self._emitted or key in self._pending:
                continue
            try:
                self._pending[key] = pdf.stat().st_size
            except OSError:
                continue
        if self._pending and not self._timer.isActive():
            self._timer.start()

    def _check_pending(self) -> None:
        still_pending: dict[str, int] = {}
        for key, last_size in self._pending.items():
            path = Path(key)
            if not path.exists():
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size == last_size and size > 0:
                self._emitted.add(key)
                self.fileReady.emit(key)
            else:
                still_pending[key] = size
        self._pending = still_pending
        # Forget files that have since disappeared (consumed and deleted), so a future
        # file that happens to reuse the same name isn't silently ignored forever.
        self._emitted = {k for k in self._emitted if Path(k).exists()}
        if not self._pending:
            self._timer.stop()
