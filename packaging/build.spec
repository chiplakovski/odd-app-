"""PyInstaller spec for the ODD Inspection Report Generator desktop build.

Run from the repo root:
    pyinstaller packaging/build.spec --noconfirm

Produces dist/ODD Inspection Report Generator/ containing the .exe plus the
assets/ and templates/ folders that app/config.py looks for next to the
frozen executable (see RESOURCE_DIR in app/config.py).
"""
from pathlib import Path

block_cipher = None

REPO_ROOT = Path(SPECPATH).resolve().parent
APP_NAME = "ODD Inspection Report Generator"

a = Analysis(
    [str(REPO_ROOT / "launcher.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=[
        (str(REPO_ROOT / "app" / "assets"), "assets"),
        (str(REPO_ROOT / "app" / "templates"), "templates"),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(REPO_ROOT / "app" / "assets" / "app_icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)
