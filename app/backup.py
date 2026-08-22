"""Export/import of all app data as a single zip file.

Settings, work list/report/hot-work history, per-item hot work checklists, and every
generated project file live only in USER_DATA_DIR - a reinstall, disk issue, or moving to
a new machine loses all of it with no way back. This lets it travel as one file.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

from .config import PRINT_INBOX_DIR, USER_DATA_DIR


def export_app_data(dest_zip: Path) -> int:
    """Zips everything under USER_DATA_DIR (settings, history, hot work checklists, and
    every project's generated files) except PrintInbox, which only ever holds transient,
    not-yet-imported print jobs. Returns the number of files written."""
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in USER_DATA_DIR.rglob("*"):
            if not path.is_file():
                continue
            try:
                path.relative_to(PRINT_INBOX_DIR)
                continue
            except ValueError:
                pass
            zf.write(path, path.relative_to(USER_DATA_DIR))
            count += 1
    return count


def import_app_data(src_zip: Path) -> int:
    """Extracts a previously exported zip back into USER_DATA_DIR, overwriting any file
    that also exists in the backup - anything else already present is left alone.
    Returns the number of files extracted."""
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src_zip, "r") as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        zf.extractall(USER_DATA_DIR)
    return len(names)
