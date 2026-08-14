"""Hot Work Permit .docx generation via direct OOXML manipulation.

The template's fillable fields are floating text boxes (not plain paragraphs
or content controls) and its checkboxes are w14 checkbox content controls.
python-docx has no first-class API for either, so this module edits the
underlying XML tree directly. See docx/hotwork template analysis: the whole
permit (both pages) is wrapped in a single top-level content control, which
this module deep-copies once per calendar day in the requested date range,
since the permit itself is only ever valid for a single day or shift.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from .config import HOTWORK_TEMPLATE
from .grouping import display_group_name
from .hotwork import HotWorkChecklist
from .models import WorkItem

_MC_NS = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
_MC_ALTERNATE_CONTENT = f"{_MC_NS}AlternateContent"
_MC_CHOICE = f"{_MC_NS}Choice"
_MC_FALLBACK = f"{_MC_NS}Fallback"

EXPECTED_TEXTBOX_COUNT = 7
EXPECTED_CHECKBOX_COUNT = 28


def default_location(item: WorkItem) -> str:
    return display_group_name(item.group) if item.group else f"Item {item.number}"


def _iter_textbox_alternates(node) -> list:
    """AlternateContent elements, each wrapping one floating text box, in document order."""
    return list(node.iter(_MC_ALTERNATE_CONTENT))


def _iter_checkbox_sdts(node) -> list:
    """w14 checkbox content-control <w:sdt> elements, in document order, any nesting depth."""
    return [
        sdt
        for sdt in node.iter(qn("w:sdt"))
        if (sdt_pr := sdt.find(qn("w:sdtPr"))) is not None and sdt_pr.find(qn("w14:checkbox")) is not None
    ]


def _set_textbox_text(alternate_content, text: str) -> None:
    """Replace a floating text box's visible text in both the modern DrawingML
    Choice branch and the legacy VML Fallback branch (Word keeps them in sync)."""
    for branch_tag in (_MC_CHOICE, _MC_FALLBACK):
        branch = alternate_content.find(branch_tag)
        if branch is None:
            continue
        txbx_content = branch.find(f".//{qn('w:txbxContent')}")
        if txbx_content is None:
            continue
        # The fillable paragraph is sometimes a direct child of the text box, and
        # sometimes nested inside an inner plain-text content control - search any depth.
        paragraphs = txbx_content.findall(f".//{qn('w:p')}")
        if not paragraphs:
            continue
        first_p = paragraphs[0]
        for extra_p in paragraphs[1:]:
            extra_p.getparent().remove(extra_p)
        # Clear a leftover "showing placeholder" flag on any inner content control so the
        # new text renders as real content instead of the gray placeholder hint.
        for placeholder_flag in list(txbx_content.iter(qn("w:showingPlcHdr"))):
            placeholder_flag.getparent().remove(placeholder_flag)
        # Preserve the first run's formatting, drop the rest of the old content.
        template_rpr = None
        first_run = first_p.find(qn("w:r"))
        if first_run is not None:
            rpr = first_run.find(qn("w:rPr"))
            if rpr is not None:
                template_rpr = deepcopy(rpr)
        for run in first_p.findall(qn("w:r")):
            first_p.remove(run)
        for proof_err in first_p.findall(qn("w:proofErr")):
            first_p.remove(proof_err)
        new_run = OxmlElement("w:r")
        if template_rpr is not None:
            new_run.append(template_rpr)
        new_t = OxmlElement("w:t")
        new_t.set(qn("xml:space"), "preserve")
        new_t.text = text
        new_run.append(new_t)
        first_p.append(new_run)


def _set_checkbox(sdt, checked: bool) -> None:
    sdt_pr = sdt.find(qn("w:sdtPr"))
    checkbox = sdt_pr.find(qn("w14:checkbox"))
    checkbox.find(qn("w14:checked")).set(qn("w14:val"), "1" if checked else "0")
    state_el = checkbox.find(qn("w14:checkedState") if checked else qn("w14:uncheckedState"))
    glyph = chr(int(state_el.get(qn("w14:val")), 16))
    # The visible glyph run sits directly in sdtContent for inline checkboxes, but is
    # nested inside a whole wrapped table cell (sdtContent > tc > p > r > t) for the
    # checklist-table checkboxes, so search recursively rather than assuming depth.
    glyph_text = next(sdt.find(qn("w:sdtContent")).iter(qn("w:t")))
    glyph_text.text = glyph


def _page_break_paragraph() -> OxmlElement:
    page_p = OxmlElement("w:p")
    p_pr = OxmlElement("w:pPr")
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:before"), "0")
    spacing.set(qn("w:after"), "0")
    spacing.set(qn("w:line"), "1")
    spacing.set(qn("w:lineRule"), "exact")
    p_pr.append(spacing)
    page_p.append(p_pr)
    run = OxmlElement("w:r")
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    run.append(br)
    page_p.append(run)
    return page_p


def _fill_permit_page(container, vessel: str, location: str, checklist: HotWorkChecklist, day: date) -> None:
    textboxes = _iter_textbox_alternates(container)
    if len(textboxes) != EXPECTED_TEXTBOX_COUNT:
        raise RuntimeError(
            f"Unexpected hot work template structure: found {len(textboxes)} text box fields, "
            f"expected {EXPECTED_TEXTBOX_COUNT}."
        )
    values = [
        vessel,
        location,
        checklist.dock_quay,
        day.strftime("%Y,%m,%d"),
        checklist.start_time,
        checklist.stop_time,
        checklist.fire_watch_motivation,
    ]
    for alternate_content, value in zip(textboxes, values):
        _set_textbox_text(alternate_content, value)

    checkboxes = _iter_checkbox_sdts(container)
    if len(checkboxes) != EXPECTED_CHECKBOX_COUNT:
        raise RuntimeError(
            f"Unexpected hot work template structure: found {len(checkboxes)} checkboxes, "
            f"expected {EXPECTED_CHECKBOX_COUNT}."
        )
    for checkbox_sdt, state in zip(checkboxes, checklist.checkbox_states()):
        _set_checkbox(checkbox_sdt, state)


def generate_hotwork_permits(
    item: WorkItem,
    vessel: str,
    checklist: HotWorkChecklist,
    start_date: date,
    end_date: date,
    output_path: Path,
    template_path: Path = HOTWORK_TEMPLATE,
) -> int:
    """Write one .docx with one permit page per calendar day in [start_date, end_date]."""
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    day_count = (end_date - start_date).days + 1
    days = [start_date + timedelta(days=i) for i in range(day_count)]

    if not template_path.exists():
        raise FileNotFoundError(f"Hot work permit template not found: {template_path}")

    doc = Document(str(template_path))
    body = doc.element.body
    original = next((el for el in body if el.tag == qn("w:sdt")), None)
    if original is None:
        raise RuntimeError("The hot work template structure is not valid (no root content control found).")
    pristine = deepcopy(original)
    body.remove(original)

    location = checklist.location.strip() or default_location(item)

    insert_index = len(body) - 1  # keep the trailing sectPr last
    for index, day in enumerate(days):
        page = deepcopy(pristine)
        _fill_permit_page(page, vessel, location, checklist, day)
        if index > 0:
            body.insert(insert_index, _page_break_paragraph())
            insert_index += 1
        body.insert(insert_index, page)
        insert_index += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return len(days)
