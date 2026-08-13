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
