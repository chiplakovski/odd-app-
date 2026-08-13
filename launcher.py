"""Standalone entry point used by the PyInstaller build (and for `python launcher.py`)."""
from app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
