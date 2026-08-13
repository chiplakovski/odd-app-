"""Hot Work Permit data model and per-item persisted checklist settings.

The permit template (see hotwork_export.py) is inherently single-day ("maximum
one day or one shift"), so a multi-day hot work window is produced as one
permit page per calendar day, all saved into a single .docx per work item.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .config import USER_DATA_DIR

HOTWORK_SETTINGS_FILE = USER_DATA_DIR / "hotwork_item_settings.json"


@dataclass
class HotWorkChecklist:
    # Work method
    welding: bool = True
    grinding: bool = False
    cutting: bool = False
    soldering: bool = False
    hot_air: bool = False
    other: bool = False
    other_text: str = ""

    # Can the combination of Method, Material & Environment cause a fire hazard?
    mme_fire_hazard: bool = True

    # Numbered checklist (page 1)
    item_0_issuer_appointed: bool = True
    item_1_operator_certified: bool = True
    fire_watch_arranged: bool = True  # 2A: competent fire-watch arranged (Yes/No)
    fire_watch_motivation: str = ""  # free text used when fire_watch_arranged is False
    item_2b_post_work_monitoring: bool = True
    item_3_confined_space_permit: bool = True
    item_4_workplace_tidy: bool = True
    item_5_combustibles_removed: bool = True
    heat_conducting_structures_present: bool = False  # 6A (Yes/No)
    item_6b_protected_accessible: bool = True
    openings_present: bool = False  # 7A (Yes/No)
    item_7b_openings_sealed: bool = True
    item_8_firefighting_equipment: bool = True
    item_9_welding_equipment_ok: bool = True
    item_10_emergency_services_reachable: bool = True

    # Automatic fire alarm / extinguishing system disconnected during the work.
    fire_alarm_disconnected: str = "yes"  # "yes" | "no" | "na"

    # Logistics
    location: str = ""  # blank = derive automatically from the work item
    dock_quay: str = "Drydock"
    start_time: str = "08:00"
    stop_time: str = "17:00"

    def checkbox_states(self) -> list[bool]:
        """The 28 checkbox states in the exact document order they appear in the template."""
        return [
            self.welding, self.grinding, self.cutting, self.soldering, self.hot_air, self.other,
            self.mme_fire_hazard, not self.mme_fire_hazard,
            self.item_0_issuer_appointed,
            self.item_1_operator_certified,
            self.fire_watch_arranged, not self.fire_watch_arranged,
            self.item_2b_post_work_monitoring,
            self.item_3_confined_space_permit,
            self.item_4_workplace_tidy,
            self.item_5_combustibles_removed,
            self.heat_conducting_structures_present, not self.heat_conducting_structures_present,
            self.item_6b_protected_accessible,
            self.openings_present, not self.openings_present,
            self.item_7b_openings_sealed,
            self.item_8_firefighting_equipment,
            self.item_9_welding_equipment_ok,
            self.item_10_emergency_services_reachable,
            self.fire_alarm_disconnected == "yes",
            self.fire_alarm_disconnected == "no",
            self.fire_alarm_disconnected == "na",
        ]


def item_settings_key(project_number: str, item_number: int) -> str:
    return f"{project_number or 'unknown'}:{item_number}"


def _load_all() -> dict[str, dict]:
    if not HOTWORK_SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(HOTWORK_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_item_checklist(key: str) -> HotWorkChecklist | None:
    row = _load_all().get(key)
    if row is None:
        return None
    try:
        return HotWorkChecklist(**row)
    except Exception:
        return None


def save_item_checklist(key: str, checklist: HotWorkChecklist) -> None:
    data = _load_all()
    data[key] = asdict(checklist)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    HOTWORK_SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
