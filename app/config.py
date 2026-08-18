"""Application constants, paths, and persisted settings."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

APP_TITLE = "ODD Inspection Report Generator"
APP_VERSION = "1.0.0"

SOURCE_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", SOURCE_DIR))
ASSET_DIR = RESOURCE_DIR / "assets"
ICON_DIR = ASSET_DIR / "icons"
TEMPLATE_DIR = RESOURCE_DIR / "templates"
MASTER_TEMPLATE = TEMPLATE_DIR / "Inspection_Master_Template.docx"
HOTWORK_TEMPLATE = TEMPLATE_DIR / "Hot_Work_Permit_Template.docx"

USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ODD Inspection Report Generator"
CONFIG_FILE = USER_DATA_DIR / "settings.json"

STATUS_VALUES = ("Finished", "In progress", "Not started", "On hold", "Cancelled", "Completed")
AUTO_EXCLUDED_GROUPS = {"ACCESS / CLEANING", "NDT / TESTING", "SUPPORT / WATCHERS"}

# Steel-range items that are excluded from the report set by default (access/support litras
# that never get their own inspection report).
AUTO_EXCLUDED_STEEL_ITEMS = {3180, 3185, 3195}

WORK_CATEGORY_PRESETS: list[tuple[str, int, int]] = [
    ("Steel", 3000, 3999),
    ("Pipe", 4000, 4999),
    ("Mechanical", 5000, 5999),
    ("Electrical", 6000, 6999),
    ("Custom", 7000, 7999),
]

# Auto-managed output layout: <app data>/ODD work/<project number>/{WO<no>.pdf, HotW/, IRep/}
WORK_ORDER_FOLDER = "ODD work"
HOTWORK_SUBFOLDER = "HotW"
INSPECTION_REPORT_SUBFOLDER = "IRep"

# Where the "oddprint" virtual printer (see packaging/) drops PDFs for pickup. The app
# watches this folder and auto-imports anything that lands here, same as loading a work
# list PDF by hand.
PRINT_INBOX_DIR = USER_DATA_DIR / "PrintInbox"


def project_output_dir(project_number: str) -> Path:
    """The auto-managed folder for one project's files: <app data>/ODD work/<project number>/.

    Lives alongside the app's own settings (USER_DATA_DIR), not the Desktop, so generated
    files aren't scattered somewhere a user could casually move or delete them outside the
    app - reach them through the app itself (History, Open Output Folder).
    """
    safe = (project_number or "Project").strip().replace(" ", "_") or "Project"
    path = USER_DATA_DIR / WORK_ORDER_FOLDER / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class ProjectInfo:
    project_name: str = ""
    project_number: str = ""
    report_date: str = ""
    inspection_company: str = "Fiducia Rederei AB"
    inspector_names: str = "Ralf Holgersson\nDavid Gustavsson"
    supervisor_company: str = "ODD"
    supervisor_name: str = "Aleksandar Chiplakovski"
    only_finished: bool = False
    inspection_method: str = "Visual inspection"
    completion_result: str = "Automatic (from work list)"


def load_settings() -> ProjectInfo:
    defaults = ProjectInfo(report_date=date.today().isoformat())
    if not CONFIG_FILE.exists():
        return defaults
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        for key in asdict(defaults):
            if key in data:
                setattr(defaults, key, data[key])
    except Exception:
        pass
    if not defaults.report_date:
        defaults.report_date = date.today().isoformat()
    return defaults


def save_settings(info: ProjectInfo) -> None:
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = asdict(info)
    data["project_name"] = ""
    data["project_number"] = ""
    data["report_date"] = date.today().isoformat()
    CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
