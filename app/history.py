"""Persisted history of processed work lists, stored alongside app settings."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .config import USER_DATA_DIR

HISTORY_FILE = USER_DATA_DIR / "work_list_history.json"
MAX_HISTORY_ENTRIES = 200


@dataclass
class HistoryEntry:
    timestamp: str
    source_name: str
    source_path: str
    project_name: str
    project_number: str
    ship_name: str
    category_name: str
    range_start: int
    range_end: int
    item_count: int
    included_count: int
    report_count: int
    output_path: str


def load_history() -> list[HistoryEntry]:
    if not HISTORY_FILE.exists():
        return []
    try:
        rows = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return [HistoryEntry(**row) for row in rows]
    except Exception:
        return []


def save_history(entries: list[HistoryEntry]) -> None:
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps([asdict(entry) for entry in entries], indent=2, ensure_ascii=False), encoding="utf-8"
    )


def add_history_entry(entry: HistoryEntry) -> list[HistoryEntry]:
    entries = [entry, *load_history()][:MAX_HISTORY_ENTRIES]
    save_history(entries)
    return entries


def clear_history() -> None:
    save_history([])
