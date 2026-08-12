"""Helpers for loading bundled images and icons."""
from __future__ import annotations

from PySide6.QtGui import QIcon

from ..config import ASSET_DIR, ICON_DIR


def asset(name: str) -> str:
    return str(ASSET_DIR / name)


def icon(name: str) -> QIcon:
    path = ICON_DIR / f"{name}.svg"
    return QIcon(str(path)) if path.exists() else QIcon()
