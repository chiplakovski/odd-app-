"""Automatic grouping of work items into report sections."""
from __future__ import annotations

import re

from .config import AUTO_EXCLUDED_STEEL_ITEMS
from .models import WorkItem

_PIPE_GROUPS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("BALLAST",), "BALLAST PIPING"),
    (("BILGE",), "BILGE PIPING"),
    (("FIRE MAIN", "FIRE LINE", "FIRE WATER"), "FIRE MAIN PIPING"),
    (("SEA WATER", "SEAWATER"), "SEA WATER PIPING"),
    (("FUEL", "HFO", "MGO", "DIESEL OIL"), "FUEL OIL PIPING"),
    (("LUBE", "LUBRICATING OIL"), "LUBE OIL PIPING"),
    (("COOLING", "COOLER"), "COOLING WATER PIPING"),
    (("COMPRESSED AIR", "AIR LINE"), "COMPRESSED AIR PIPING"),
    (("STEAM",), "STEAM PIPING"),
    (("HYDRAULIC",), "HYDRAULIC PIPING"),
    (("SEWAGE", "GREY WATER", "BLACK WATER", "SANITARY"), "SANITARY PIPING"),
    (("VALVE", "COCK"), "VALVES / COCKS"),
)

_MECHANICAL_GROUPS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("PROPELLER", "SHAFT", "RUDDER", "THRUSTER", "STERN TUBE"), "PROPULSION / STEERING"),
    (("PUMP",), "PUMPS"),
    (("MAIN ENGINE", "AUXILIARY ENGINE", "ENGINE"), "ENGINES"),
    (("WINCH", "WINDLASS", "CAPSTAN"), "DECK MACHINERY"),
    (("CRANE", "DAVIT"), "CRANES / DAVITS"),
    (("COMPRESSOR",), "COMPRESSORS"),
    (("HVAC", "VENTILATION", "FAN"), "HVAC / VENTILATION"),
    (("GEARBOX", "GEAR BOX"), "GEARBOXES"),
)


def _steel_group(item: WorkItem, title: str, t: str) -> str:
    if "ANODE" in title or "ANODIC" in title or "ZINC" in title:
        return "ANODES"
    if "ROPE GUARD" in title or "SHAFT CLEARANCE" in title:
        return "ROPE GUARD"
    if "MANHOLE" in title or "MANHOLE" in t:
        return "MANHOLES"
    if "CARGO HOLD" in title or "HATCH COVER" in t or "CLIT" in t or "SKALKAR" in title:
        return "CARGO HOLD / HATCH COVER"
    if "FOREPEAK" in title or "CHAIN LOCKER" in title:
        return "FOREPEAK / CHAIN LOCKER"
    if "BREAK DOWN FOLLOWING LITTRA" in t and "SWBT 1" in t:
        return "SWBT 1"
    if "BULKHEAD" in t and title.startswith("STEEL REPAIR IN SWBT"):
        return "SWBT BULKHEADS"
    swbt_nums = sorted(set(re.findall(r"SWBT\s*([1-9])", t)))
    if swbt_nums:
        return "SWBT " + "/".join(swbt_nums)
    dwbt_nums = sorted(set(re.findall(r"(?:DWBT|DBWT)\s*([1-9])", t)))
    if dwbt_nums:
        return "DWBT STEEL REPAIRS"
    if "MAST" in t or "BRIDGE" in t or "ELECTRICAL BOX" in t or "CABLE" in t:
        return "DECK / MAST / BRIDGE"
    if "STEEL REPAIR" in title or "STEEL WORK" in title:
        return "GENERAL STEEL REPAIR"
    return f"STEEL {item.number // 100 * 100} SERIES"


def _pipe_group(item: WorkItem, t: str) -> str:
    for keywords, group in _PIPE_GROUPS:
        if any(keyword in t for keyword in keywords):
            return group
    return f"PIPE {item.number // 100 * 100} SERIES"


def _mechanical_group(item: WorkItem, t: str) -> str:
    for keywords, group in _MECHANICAL_GROUPS:
        if any(keyword in t for keyword in keywords):
            return group
    return f"MECHANICAL {item.number // 100 * 100} SERIES"


def _electrical_group(item: WorkItem, t: str) -> str:
    if "LIGHT" in t:
        return "LIGHTING"
    if "CABLE" in t or "PENETRATION" in t:
        return "CABLES / PENETRATIONS"
    if "MOTOR" in t:
        return "ELECTRIC MOTORS"
    if "ALARM" in t or "CONTROL" in t or "SENSOR" in t:
        return "ALARMS / CONTROL"
    return f"ELECTRICAL {item.number // 100 * 100} SERIES"


def grouping_key(item: WorkItem) -> str:
    lines = [x.strip() for x in item.description.splitlines() if x.strip()]
    title = (lines[0] if lines else item.summary).upper()
    t = (item.description + " " + item.summary).upper().replace("AFT MUST", "AFT MAST")

    # Common support scopes that normally should not become final inspection reports.
    if "FIRE WATCH" in title or "TANK WATCH" in title or "CONFINED SPACE" in title:
        return "SUPPORT / WATCHERS"
    if "ACCESS WORK" in title or "TANK CLEANING" in title:
        return "ACCESS / CLEANING"
    if "NDT" in title or "VACUUM BOX" in title or "MPI" in title:
        return "NDT / TESTING"

    if 3000 <= item.number <= 3999:
        return _steel_group(item, title, t)
    if 4000 <= item.number <= 4999:
        return _pipe_group(item, t)
    if 5000 <= item.number <= 5999:
        return _mechanical_group(item, t)
    if 6000 <= item.number <= 6999:
        return _electrical_group(item, t)
    return f"ITEMS {item.number // 100 * 100} SERIES"


def apply_auto_grouping(items: list[WorkItem], mode: str = "balanced") -> None:
    mode = mode.lower()
    if mode == "none":
        for item in items:
            item.group = f"ITEM {item.number}"
        return
    for item in items:
        item.group = grouping_key(item)
    if mode == "maximum":
        for item in items:
            key = item.group
            if 3000 <= item.number <= 3999:
                if key.startswith("SWBT"):
                    item.group = "SWBT STEEL REPAIRS"
                elif key.startswith("DWBT"):
                    item.group = "DWBT STEEL REPAIRS"
                elif key in {"FOREPEAK / CHAIN LOCKER", "GENERAL STEEL REPAIR"}:
                    item.group = "TANK STEEL REPAIRS"
            elif 4000 <= item.number <= 4999:
                item.group = "PIPE WORK"
            elif 5000 <= item.number <= 5999:
                item.group = "MECHANICAL WORK"
            elif 6000 <= item.number <= 6999:
                item.group = "ELECTRICAL WORK"
            else:
                item.group = f"ITEMS {item.number // 1000 * 1000} SERIES"


def apply_steel_auto_exclusions(items: list[WorkItem], start_item: int, end_item: int) -> None:
    """Exclude known access/support litras when the selected range covers the Steel series."""
    if not (start_item <= 3180 <= end_item):
        return
    for item in items:
        if item.number in AUTO_EXCLUDED_STEEL_ITEMS:
            item.included = False


def group_items(items: list[WorkItem], only_finished: bool = True) -> list[list[WorkItem]]:
    grouped: dict[str, list[WorkItem]] = {}
    order: list[str] = []
    for item in items:
        if not item.included:
            continue
        if only_finished and item.status.lower() not in {"finished", "completed"}:
            continue
        key = item.group.strip() or f"ITEM {item.number}"
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(item)
    return [grouped[k] for k in order]
