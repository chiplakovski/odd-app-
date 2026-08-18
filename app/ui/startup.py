"""Registers (or unregisters) the app to launch at Windows login, so it's already running
- watching the Print Inbox in the background - by the time anything gets printed to it,
instead of only catching prints while someone happens to have the app open.

Uses the per-user HKCU Run key rather than a Startup-folder shortcut: it's the same
mechanism most desktop apps use for a "start with Windows" option, and writing to HKCU
needs no admin rights (unlike HKLM, which is machine-wide).
"""
from __future__ import annotations

import sys

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "ODD Inspection Report Generator"

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import winreg


def _launch_command() -> str:
    # Under PyInstaller, sys.executable is the frozen app's own .exe; --tray tells
    # app/main.py to start hidden in the tray instead of showing the window immediately.
    return f'"{sys.executable}" --tray'


def set_start_at_login(enabled: bool) -> bool:
    """Best-effort; returns whether the registry change actually succeeded."""
    if not IS_WINDOWS:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, _launch_command())
            else:
                try:
                    winreg.DeleteValue(key, _VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False
