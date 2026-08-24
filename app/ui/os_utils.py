"""Cross-platform "open this file/folder with the system default app" helper."""
from __future__ import annotations

import os
import subprocess
import sys


def open_with_system_default(path: str) -> bool:
    try:
        if hasattr(os, "startfile"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
        return True
    except Exception:
        return False


def pin_to_quick_access(path: str) -> bool:
    """Pins a folder to Windows' Quick Access, the same navigation pane shown by File
    Explorer and by native Save/Open dialogs - including "Microsoft Print to PDF"'s Save
    dialog. That folder-tree navigation to the Print Inbox folder is the main manual step
    in printing a work list into the app, so pinning it there cuts that down to one click.
    Quick Access pins are stored per-user (no admin rights or driver install needed) -
    Windows only, and best-effort: silently returns False anywhere else or on any failure.
    """
    if not hasattr(os, "startfile"):
        return False
    try:
        import win32com.client

        shell = win32com.client.Dispatch("Shell.Application")
        namespace = shell.Namespace(path)
        if namespace is None:
            return False
        namespace.Self.InvokeVerb("pintohome")
        return True
    except Exception:
        return False
