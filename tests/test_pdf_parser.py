"""Regression tests for app/pdf_parser.py.

Each test below reproduces the exact shape of a real bug found (and fixed) against real
customer work-list PDFs: a fake department-heading item leaking through as a zero-content
work item, a blank Shipowner No. column swallowing an item's actual description text,
Swedish status words not being recognized, and a date-log entry losing its wrapped
continuation line and gluing it onto unrelated content. These use small synthetic
"layout mode" text blocks (not the real customer PDFs, which may be sensitive) built to
match the column layout `extract_pdf_text` actually produces.
"""
from __future__ import annotations

from app.pdf_parser import _combine_wrapped_lines, _is_heading_only, _normalize_status, make_summary, parse_work_items

# Real work lists render the Text column very wide - the gap between "Text" and "Status"
# in the header line routinely spans 90-150+ characters (confirmed against real customer
# PDFs). Using a similarly wide gap here matters: it's what originally let a short row's
# Status appear far to the right of a much narrower Text value without merging into it.
TEXT_POS = 41
STATUS_POS = 137


def _header_line(text_pos: int = TEXT_POS, status_pos: int = STATUS_POS) -> str:
    line = "Item".ljust(8) + "Shipowner No."
    line = line.ljust(text_pos) + "Text"
    line = line.ljust(status_pos) + "Status"
    return line


def _row(item_number: int, owner: str = "", text: str = "", status: str = "",
         text_pos: int = TEXT_POS, status_pos: int = STATUS_POS) -> str:
    """One item's header row, with owner/text/status placed at realistic column offsets.
    An empty field is simply omitted, the same as a blank PDF table cell."""
    line = str(item_number)
    if owner:
        line = line.ljust(8) + owner
    if text:
        line = line.ljust(text_pos) + text
    if status:
        line = line.ljust(status_pos) + status
    return line


def _continuation(text: str, text_pos: int = TEXT_POS) -> str:
    return " " * text_pos + text


def _table(rows: list[str], text_pos: int = TEXT_POS, status_pos: int = STATUS_POS) -> str:
    return "\n".join([_header_line(text_pos, status_pos), *rows])


# --- Heading / banner exclusion -------------------------------------------------------


def test_asterisk_banner_excluded():
    text = _table([
        _row(3000, text="****** Steel works ******"),
        _row(3010, owner="- 111 - Pos 1", text="Renew steel plate in way of frame 45.", status="Finished"),
    ])
    items = parse_work_items(text, "124-000", 3000, 3999)
    assert [i.number for i in items] == [3010]


def test_department_heading_singular_and_plural_excluded():
    for wording in ("STEEL WORK", "STEEL WORKS"):
        text = _table([
            _row(3000, text=wording),
            _row(3010, owner="- 111 - Pos 1", text="Renew steel plate in way of frame 45.", status="Finished"),
        ])
        items = parse_work_items(text, "124-000", 3000, 3999)
        assert [i.number for i in items] == [3010], f"failed for wording={wording!r}"


def test_unenumerated_banner_with_blank_owner_and_status_excluded():
    """Department dividers aren't limited to the words _HEADING_ONLY_RE enumerates -
    "LSA & SAFETY EQUIPMENT" and "INTERIOR / INSULATION WORKS" both slipped through as
    fake items until the blank-owner/blank-status/all-caps heuristic was added."""
    for heading in ("LSA & SAFETY EQUIPMENT", "INTERIOR / INSULATION WORKS", "VARIOUS WORKS"):
        text = _table([
            _row(8000, text=heading),
            _row(8010, owner="01.01", text="Supply new gaskets material.", status="Finished"),
        ])
        items = parse_work_items(text, "124-000", 8000, 8999)
        assert [i.number for i in items] == [8010], f"failed for heading={heading!r}"


def test_real_short_item_with_blank_owner_and_status_is_kept_when_not_all_caps():
    """A genuine (if unusual) short item with no owner/status, but not all-caps, must
    not be mistaken for a heading banner."""
    text = _table([
        _row(9010, text="Lunch for crew on 2026-08-20."),
    ])
    items = parse_work_items(text, "124-000", 9000, 9999)
    assert [i.number for i in items] == [9010]
    assert items[0].summary == "Lunch for crew on 2026-08-20."


def test_short_all_caps_item_with_owner_is_kept():
    text = _table([
        _row(2700, owner="02.01", text="WATER BALLAST TANK TREATMENT", status="Finished"),
    ])
    items = parse_work_items(text, "124-000", 2000, 2999)
    assert [i.number for i in items] == [2700]


def test_is_heading_only_unit():
    assert _is_heading_only("STEEL WORKS") is True
    assert _is_heading_only("****** Steel works ******") is True
    assert _is_heading_only("LSA & SAFETY EQUIPMENT") is True
    assert _is_heading_only("Lunch for crew on 2026-08-20.") is False
    assert _is_heading_only("WATER BALLAST TANK TREATMENT", owner_no="02.01") is False
    assert _is_heading_only("Renew steel plate.\nSecond line.") is False


def test_is_heading_only_regex_matches_plural_works_specifically():
    """Isolates _HEADING_ONLY_RE itself (not the blank-owner/status heuristic, which
    would also catch this) by supplying a populated owner - the enumerated regex
    originally only matched singular "WORK" and missed "STEEL WORKS"."""
    assert _is_heading_only("STEEL WORKS", owner_no="01.01") is True
    assert _is_heading_only("STEEL WORK", owner_no="01.01") is True


# --- Column parsing robustness ---------------------------------------------------------


def test_populated_owner_column_parses_correctly():
    text = _table([
        _row(3010, owner="- 111 - Pos 1", text="Renew steel plate in way of frame 45.", status="Finished"),
    ])
    items = parse_work_items(text, "124-000", 3000, 3999)
    assert len(items) == 1
    item = items[0]
    assert item.owner_no == "- 111 - Pos 1"
    assert item.status == "Finished"
    assert item.summary == "Renew steel plate in way of frame 45."


def test_blank_owner_column_still_captures_text():
    """The originally-reported bug: item 3050's "Rope guard off and on..." text went
    missing entirely when the Shipowner No. column was blank, because splitting a row
    into fields by whitespace gaps alone (with no owner value to anchor on) shifted the
    real Text content into the owner slot and lost it."""
    text = _table([
        _row(3050, text="Rope guard off and on for measuring of shaft clearance.", status="Finished"),
        _continuation("Scaffolding to be charged separately."),
        _continuation("Including padeyes 2 pcs"),
    ])
    items = parse_work_items(text, "124-073", 3000, 3999)
    assert len(items) == 1
    item = items[0]
    assert item.owner_no == ""
    assert item.status == "Finished"
    assert item.summary.startswith("Rope guard off and on for measuring of shaft clearance.")
    assert "Scaffolding to be charged separately." in item.summary


def test_column_position_drift_still_parses_correctly():
    """Real work lists don't render the header and every data row at exactly the same
    character offsets from page to page. A row's Text/Status a few characters off from
    the header's own position must still land in the right field."""
    drifted_text_pos = TEXT_POS + 4
    drifted_status_pos = STATUS_POS - 3
    text = _table(
        [_row(3050, owner="- 12345 - Pos 10", text="Rope guard off and on for measuring of shaft clearance.",
              status="Finished", text_pos=drifted_text_pos, status_pos=drifted_status_pos)],
    )
    items = parse_work_items(text, "124-073", 3000, 3999)
    assert len(items) == 1
    assert items[0].owner_no == "- 12345 - Pos 10"
    assert items[0].status == "Finished"
    assert items[0].summary.startswith("Rope guard off and on for measuring of shaft clearance.")


# --- Status normalization ---------------------------------------------------------------


def test_status_exact_values():
    text = _table([_row(3010, owner="01.01", text="Some work.", status="In progress")])
    items = parse_work_items(text, "124-000", 3000, 3999)
    assert items[0].status == "In progress"


def test_status_swedish_aliases():
    assert _normalize_status("Klart") == "Finished"
    assert _normalize_status("Pågår") == "In progress"
    assert _normalize_status("Pagar") == "In progress"
    assert _normalize_status("Pending") == "On hold"
    assert _normalize_status("Utgår") == "Cancelled"
    assert _normalize_status("Utgar") == "Cancelled"


def test_status_glued_to_trailing_reference_code():
    """Some work lists (Swedish Navy / Saab Kockums exports) glue a status word directly
    to an unrelated trailing reference code with no separating space."""
    assert _normalize_status("KlartMIMI: 255") == "Finished"
    assert _normalize_status("PågårFU-326") == "In progress"
    assert _normalize_status("UtgårAU-255.03 Wet bell") == "Cancelled"


def test_status_alias_end_to_end():
    text = _table([_row(3010, owner="MIMI: 255", text="Some hull work.", status="Klart")])
    items = parse_work_items(text, "124-000", 3000, 3999)
    assert items[0].status == "Finished"


# --- Summary construction ---------------------------------------------------------------


def test_date_log_entry_wrapped_across_lines_fully_removed():
    """A date-prefixed progress-log entry ("16/8 Install doors ... watertightness
    testing.") that wraps onto a second physical PDF line must be removed as one unit -
    the un-prefixed continuation line must not survive and glue onto unrelated content."""
    description = (
        "Dismounting of the cargo holds 3 metal doors, straightening and adjusting\n"
        "of the hinges.\n"
        "16/8 Install doors, weld new hinges, and prepare for watertightness\n"
        "testing."
    )
    summary = make_summary(description, 3100)
    assert "testing." not in summary
    assert "16/8" not in summary
    assert summary == "Dismounting of the cargo holds 3 metal doors, straightening and adjusting of the hinges."


def test_combine_wrapped_lines_does_not_split_on_semicolon():
    """A semicolon is mid-sentence punctuation, not a sentence terminator - a PDF line
    wrap right after one must still combine into a single logical line, unlike a wrap
    after '.' or ':' which correctly stays split."""
    lines = ["Straightening the door foundation inside and cutting the hinges;", "prepare for installing new."]
    combined = _combine_wrapped_lines(lines)
    assert combined == ["Straightening the door foundation inside and cutting the hinges; prepare for installing new."]


def test_semicolon_wrap_combines_into_one_sentence():
    """End-to-end: a sentence that happens to wrap onto the next physical PDF line right
    after a semicolon, inside a date-prefixed progress-log entry, must be combined and
    removed as one unit - not left with its un-prefixed continuation ("prepare for
    installing new.") surviving on its own as an orphaned fragment."""
    description = (
        "13/8 Straightening the door foundation inside and cutting the hinges;\n"
        "prepare for installing new."
    )
    summary = make_summary(description, 3100)
    assert "prepare for installing new." not in summary.split("\n")
    # The whole entry is a date-log line and gets fully removed - make_summary falls
    # back to a placeholder rather than ever returning an empty summary.
    assert summary == "Work under item 3100."


def test_colon_headed_section_stays_separate():
    description = "Scope of work:\n- Full UHP blasting by robot/gun\n- Cleaning"
    summary = make_summary(description, 2830)
    lines = summary.split("\n")
    assert lines[0] == "Scope of work:"
    assert lines[1] == "- Full UHP blasting by robot/gun"


def test_sketch_lines_suppressed_after_three():
    description = "\n".join([f"Sketch {n} attached." for n in range(1, 8)])
    summary = make_summary(description, 3010)
    assert summary.count("Sketch") == 3


def test_long_description_is_not_truncated():
    """Regression guard for the original "text isn't complete" bug: no length or
    line-count cap should cut off a long real description."""
    lines = [f"Detail line number {n} describing the work performed on the item." for n in range(30)]
    description = "\n".join(lines)
    summary = make_summary(description, 3010)
    assert summary == description
    assert len(summary) > 720
