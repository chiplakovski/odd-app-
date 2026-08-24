"""Tests for app/hotwork_export.py's default_location() - the auto-derived text for the
Hot Work Permit's Location field, which must always fit within LOCATION_MAX_CHARS once
the UI prefixes it with "<item number> - ", still leaving room for the user to add their
own detail (see dialogs.py's HotWorkDialog).
"""
from __future__ import annotations

from app.hotwork_export import LOCATION_MAX_CHARS, default_location
from app.models import WorkItem

ITEM_NUMBER_PREFIX_LEN = len("3200 - ")  # 4-digit item number + " - "


def _item(description: str = "", summary: str = "", group: str = "") -> WorkItem:
    return WorkItem(number=3200, owner_no="", status="", description=description, summary=summary, group=group)


def test_short_description_returned_unchanged():
    item = _item(summary="Forecastle area")
    assert default_location(item) == "Forecastle area"


def test_long_description_truncated_with_headroom_for_user_additions():
    item = _item(summary="Cargo hold #3 Bhd with E/R repairs 8/8 inspect the work with the crew")
    result = default_location(item)
    assert result.endswith("...")
    # After the UI's "<item number> - " prefix, there must be real room left under
    # LOCATION_MAX_CHARS for the user to add their own detail, not just barely fit.
    prefixed_len = ITEM_NUMBER_PREFIX_LEN + len(result)
    assert prefixed_len < LOCATION_MAX_CHARS
    headroom = LOCATION_MAX_CHARS - prefixed_len
    assert headroom >= 15, f"only {headroom} characters of headroom left for user additions"


def test_truncation_breaks_on_a_word_boundary():
    """Truncation must cut at the last full word before the limit (rsplit(" ", 1)), not
    mid-word, so the "..." doesn't dangle off a chopped-off word fragment."""
    item = _item(summary="Cargo hold #3 Bhd with E/R repairs 8/8 inspect the work with the crew")
    result = default_location(item)
    core = result[:-3]  # strip the trailing "..."
    assert core == core.rstrip()
    assert "Cargo hold #3 Bhd with E/R repairs 8/8 inspect the work with the crew".startswith(core)


def test_falls_back_to_group_name_when_no_description():
    item = _item(group="CARGO HOLD / HATCH COVER")
    assert default_location(item) == "Cargo Hold / Hatch Cover"


def test_falls_back_to_item_number_when_nothing_else_available():
    item = _item()
    assert default_location(item) == "Item 3200"
