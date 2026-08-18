"""Auto-fills the native "Save Print Output As" dialog that Windows' built-in
"Microsoft Print to PDF" printer always shows, so printing to it feels as automatic as
a real virtual printer without installing any driver (which would need admin rights -
see packaging/installer.iss history and the "no admin" decision in this feature).

This is Windows-only UI automation via pywin32, not a print driver: it polls for a
standard common-dialog window (class "#32770") whose title matches the print-output
save dialog, points its filename field at config.PRINT_INBOX_DIR with a generated name,
and confirms it - PrintInboxWatcher then picks up the resulting file exactly like any
other PDF dropped there.

It's inherently best-effort: the exact dialog title depends on Windows' display language
and can vary. Every "#32770" dialog title this doesn't recognize gets appended to
_DEBUG_LOG_PATH (capped in size) - if auto-catch doesn't fire, that file's last lines are
the exact title text to add to _TITLE_FRAGMENTS below.
"""
from __future__ import annotations

import sys
from datetime import datetime

from PySide6.QtCore import QObject, QTimer

from ..config import PRINT_INBOX_DIR, USER_DATA_DIR

_POLL_INTERVAL_MS = 400
_DEBUG_LOG_PATH = USER_DATA_DIR / "print_catcher_debug.log"
_DEBUG_LOG_MAX_LINES = 50

# Fragments matched case-insensitively against a "#32770" dialog's title. Windows'
# actual wording for the Print-to-PDF save dialog varies by display language; English
# and Swedish (this app's primary locale) are covered. If auto-catch silently doesn't
# fire, check _DEBUG_LOG_PATH for the real title and add a fragment here.
_TITLE_FRAGMENTS = (
    "save print output",  # English
    "spara utskrift",  # Swedish
)

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        import win32con
        import win32gui

        _PYWIN32_AVAILABLE = True
    except ImportError:
        _PYWIN32_AVAILABLE = False
else:
    _PYWIN32_AVAILABLE = False


def _log_unmatched_title(title: str) -> None:
    try:
        lines = []
        if _DEBUG_LOG_PATH.exists():
            lines = _DEBUG_LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
        lines.append(f"{datetime.now().isoformat(timespec='seconds')}  {title!r}")
        lines = lines[-_DEBUG_LOG_MAX_LINES:]
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        _DEBUG_LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass


def _find_edit_child(hwnd) -> int | None:
    """Depth-first search for the innermost Edit control (the filename field) - Vista-style
    common dialogs nest it inside ComboBoxEx32/ComboBox wrappers, so a shallow search misses it."""
    found: list[int] = []

    def _visit(parent: int) -> None:
        def _cb(child: int, _param) -> bool:
            cls = win32gui.GetClassName(child)
            if cls == "Edit":
                found.append(child)
            _visit(child)
            return True

        win32gui.EnumChildWindows(parent, _cb, None)

    _visit(hwnd)
    return found[-1] if found else None


def _matches_target_dialog(hwnd) -> bool:
    if win32gui.GetClassName(hwnd) != "#32770":
        return False
    title = win32gui.GetWindowText(hwnd)
    if not title:
        return False
    lowered = title.lower()
    if any(fragment in lowered for fragment in _TITLE_FRAGMENTS):
        return True
    _log_unmatched_title(title)
    return False


class PrintDialogCatcher(QObject):
    """Watches for the Print-to-PDF save dialog and auto-completes it into PRINT_INBOX_DIR.

    No-op on anything but Windows (or if pywin32 isn't installed), so it's safe to
    instantiate unconditionally from MainWindow.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._seen: set[int] = set()
        self._timer: QTimer | None = None
        if not (IS_WINDOWS and _PYWIN32_AVAILABLE):
            return
        self._timer = QTimer(self)
        self._timer.setInterval(_POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    def _poll(self) -> None:
        live: set[int] = set()

        def _cb(hwnd, _param) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            live.add(hwnd)
            if hwnd not in self._seen:
                self._seen.add(hwnd)
                if _matches_target_dialog(hwnd):
                    self._fill_and_save(hwnd)
            return True

        win32gui.EnumWindows(_cb, None)
        # Forget handles for dialogs that have since closed, so a future dialog reusing
        # the same handle value is inspected fresh rather than skipped.
        self._seen &= live

    def _fill_and_save(self, hwnd) -> None:
        edit = _find_edit_child(hwnd)
        if edit is None:
            return
        PRINT_INBOX_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"Print_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        target = str(PRINT_INBOX_DIR / filename)
        win32gui.SendMessage(edit, win32con.WM_SETTEXT, 0, target)
        # IDOK (control id 1) is the standard "Save"/"OK" affirmative action id Windows
        # assigns in GetSaveFileName-family common dialogs, regardless of the button's
        # localized label.
        win32gui.PostMessage(hwnd, win32con.WM_COMMAND, 1, 0)


def make_print_dialog_catcher(parent: QObject | None = None) -> PrintDialogCatcher:
    return PrintDialogCatcher(parent)
