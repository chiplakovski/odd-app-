"""Persisted history of processed work lists, stored alongside app settings."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .config import USER_DATA_DIR

HISTORY_FILE = USER_DATA_DIR / "work_list_history.json"


@dataclass
class HistoryEntry:
    timestamp: str
    kind: str = "reports"  # "reports" (inspection reports) | "hotwork" (hot work permits)
    source_name: str = ""
    source_path: str = ""
    project_name: str = ""
    project_number: str = ""
    ship_name: str = ""
    category_name: str = ""
    range_start: int = 0
    range_end: int = 0
    item_count: int = 0
    included_count: int = 0
    report_count: int = 0
    output_path: str = ""
    # hot work permit specifics
    item_number: int | None = None
    date_from: str = ""
    date_to: str = ""


def load_history() -> list[HistoryEntry]:
    if not HISTORY_FILE.exists():
        return []
    try:
        rows = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    entries = []
    for row in rows:
        try:
            entries.append(HistoryEntry(**row))
        except Exception:
            continue
    return entries


def save_history(entries: list[HistoryEntry]) -> None:
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps([asdict(entry) for entry in entries], indent=2, ensure_ascii=False), encoding="utf-8"
    )


def add_history_entry(entry: HistoryEntry) -> list[HistoryEntry]:
    entries = [entry, *load_history()]
    save_history(entries)
    return entries


def clear_history() -> None:
    save_history([])
