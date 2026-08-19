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

# The app uses QtCore/QtGui/QtWidgets (plus SVG icon rendering), QtPdf/QtPdfWidgets (the
# in-app report viewer) and QtPrintSupport (print/print preview). This trims the Qt
# submodules that are pure Python-level extras (QtTest, QtDesigner, QtHelp, ...). Most of
# PySide6's bundle size is Qt's own binary-level dependencies between Core/Gui/Widgets and
# things like Network/Qml (pulled in by PyInstaller's Qt dependency walker regardless of
# excludes, confirmed by testing), so don't expect this list to shrink the build dramatically
# - it's a small, safe trim, not the fix for a slow first launch (that's almost always
# Windows Defender/antivirus scanning the freshly-installed exe, which only happens once).
UNUSED_QT_MODULES = [
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtQuickControls2",
    "PySide6.QtQuickTest", "PySide6.QtQuick3D", "PySide6.QtQuick3DAssetImport",
    "PySide6.QtQuick3DRuntimeRender", "PySide6.QtQuick3DUtils",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel", "PySide6.QtWebSockets",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetwork", "PySide6.QtSql", "PySide6.QtXml",
    "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning", "PySide6.QtLocation",
    "PySide6.QtSensors", "PySide6.QtSerialPort",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs", "PySide6.QtGraphsWidgets",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput", "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
    "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtStateMachine",
    "PySide6.QtSpatialAudio", "PySide6.QtTextToSpeech",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtVirtualKeyboard",
    "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtUiTools",
]

a = Analysis(
    [str(REPO_ROOT / "launcher.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=[
        (str(REPO_ROOT / "app" / "assets"), "assets"),
        (str(REPO_ROOT / "app" / "templates"), "templates"),
    ],
    # win32com/pythoncom back the Word COM automation used to convert generated reports
    # to PDF (Windows-only, see app/pdf_export.py) - imported inside a platform guard so
    # PyInstaller's static bytecode scan should already find them, but hiddenimports is
    # cheap insurance since this can't be verified without a real Windows build.
    hiddenimports=["win32com", "win32com.client", "pythoncom", "pywintypes"],
    hookspath=[],
    runtime_hooks=[],
    excludes=UNUSED_QT_MODULES,
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
