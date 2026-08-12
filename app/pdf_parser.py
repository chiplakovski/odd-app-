"""PDF work-list text extraction and parsing into WorkItem records."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from .config import AUTO_EXCLUDED_GROUPS, STATUS_VALUES
from .grouping import grouping_key
from .models import WorkItem

_HEADING_ONLY_RE = re.compile(
    r"(?:STEEL|PIPE|PIPING|MECHANICAL|ELECTRICAL|OUTFITTING|PAINT|CARPENTRY|INSULATION)\s+WORK"
)


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text(extraction_mode="layout") or "")
    return "\n".join(chunks)


def detect_project(text: str, source_path: Path) -> tuple[str, str]:
    for raw in text.splitlines()[:60]:
        line = " ".join(raw.strip().split())
        m = re.match(r"^(\d{3}-\d{3})\s+(.+?)$", line)
        if m:
            name = re.sub(r"\s+\d+\s*/\s*\d+$", "", m.group(2)).strip()
            return name, m.group(1)
    stem = source_path.stem
    m = re.search(r"(\d{3}-\d{3})", stem)
    number = m.group(1) if m else ""
    name = stem.replace(number, "").replace("steel", "").replace("worklist", "").strip(" -_")
    return name.upper(), number


def _match_item_header(line: str) -> tuple[int, str, str] | None:
    clean = " ".join(line.strip().split())
    if not clean:
        return None
    status_re = "|".join(re.escape(s) for s in STATUS_VALUES)
    m = re.match(rf"^(\d{{4}})(?:\s+(\S+?))?\s+({status_re})$", clean, flags=re.I)
    if m:
        number = int(m.group(1))
        owner = (m.group(2) or "").strip()
        status = next((s for s in STATUS_VALUES if s.lower() == m.group(3).lower()), m.group(3))
        return number, owner, status
    m = re.match(r"^(\d{4})(?:\s+(\S+))?$", clean)
    if m:
        return int(m.group(1)), (m.group(2) or "").strip(), ""
    return None


def _is_page_noise(line: str, project_number: str = "") -> bool:
    s = " ".join(line.strip().split())
    if not s:
        return False
    if project_number and s.startswith(project_number + " "):
        return True
    patterns = [
        r"^TextItem Shipowner No\.?$",
        r"^Item Shipowner No\.? Text$",
        r"^Status$",
        r"^\d+\s*/\s*\d+$",
        r"^\d{4}-\d{2}-\d{2}$",
        r"^Item No:\s*\d{4}\s*[-–]\s*\d{4}$",
        r"^STEEL WORK:$",
        r"^PIPE WORK:$",
    ]
    return any(re.match(p, s, flags=re.I) for p in patterns)


def _is_layout_noise_fragment(text: str) -> bool:
    s = " ".join(text.strip().split())
    if not s:
        return True
    # Date/page fragments from the repeated PDF header can fall inside the Text column.
    if len(s) <= 24 and re.match(r"^20\d{2}-", s):
        return True
    if len(s) <= 8 and re.fullmatch(r"\d+\s*/?", s):
        return True
    if len(s) <= 12 and re.fullmatch(r"\d+\s*/\s*\d+", s):
        return True
    return False


def clean_description_lines(lines: Iterable[str]) -> list[str]:
    result: list[str] = []
    for raw in lines:
        line = " ".join(raw.strip().split())
        if not line:
            continue
        line = re.sub(r"^[-–—_]{4,}\s*", "", line)
        line = re.sub(r"\s*[-–—_]{4,}$", "", line)
        if not line:
            continue
        if re.fullmatch(r"[-–—_]{4,}", line):
            continue
        if re.match(r"^\d+\s*/\s*\d+$", line):
            continue
        result.append(line)
    return result


def _combine_wrapped_lines(lines: list[str]) -> list[str]:
    combined: list[str] = []
    for line in lines:
        if not combined:
            combined.append(line)
            continue
        is_new = (
            line.startswith(("-", "•"))
            or re.match(
                r"^(Sketch|Original|ODD|Scope|Repair|Renewal|Supply|Removal|Steel|Cargo|Forepeak|"
                r"Chain|DWBT|DBWT|SWBT|Frame|Close|Manhole|Aft|Electrical|Rope)",
                line,
                flags=re.I,
            )
            or combined[-1].endswith((".", ":", ";"))
        )
        if is_new:
            combined.append(line)
        else:
            combined[-1] += " " + line
    return combined


def make_summary(description: str, item_number: int) -> str:
    lines = [x.strip() for x in description.splitlines() if x.strip()]
    filtered: list[str] = []
    for line in lines:
        low = line.lower()
        if re.match(r"^-?\s*\d{1,2}/\d{1,2}(?:/\d{2,4})?\s*:?[\s-]", line):
            continue
        if low.startswith(("meeting ", "calculated with", "in account", "requoted accordingly")):
            continue
        if any(
            phrase in low
            for phrase in (
                "inspect and arrange",
                "inspect and supervise",
                "supervision",
                "assist and supervise",
                "proceed with works",
                "hold by the client",
                "new marking to be provided",
            )
        ):
            continue
        filtered.append(line)

    combined = _combine_wrapped_lines(filtered)
    # Prefer scope/location and measurable outcome; suppress repetitive sketch lists.
    chosen: list[str] = []
    sketch_count = 0
    for line in combined:
        if line.lower().startswith("sketch"):
            sketch_count += 1
            if sketch_count > 3:
                continue
        if line not in chosen:
            chosen.append(line)
        if len(chosen) >= 7:
            break
    if not chosen:
        chosen = combined[:5] or [f"Work under item {item_number}."]
    summary = "\n".join(chosen)
    if len(summary) > 720:
        summary = summary[:717].rsplit(" ", 1)[0] + "..."
    return summary


def _is_heading_only(description: str) -> bool:
    title = description.strip().upper().rstrip(":")
    return bool(title) and bool(_HEADING_ONLY_RE.fullmatch(title))


def parse_work_items(
    text: str,
    project_number: str = "",
    start_item: int = 3000,
    end_item: int = 3999,
) -> list[WorkItem]:
    """Parse a selected litra/item range from a work-list PDF.

    Ranges are inclusive. Examples:
      Steel: 3000-3999
      Pipe: 4000-4999
      Mechanical: 5000-5999

    The parser scans the complete PDF and only collects items inside the selected
    range, so the same work list can be reused for different departments.
    """
    if start_item > end_item:
        start_item, end_item = end_item, start_item

    items = _parse_columnar(text, project_number, start_item, end_item)
    if not items:
        items = _parse_fallback(text, project_number, start_item, end_item)

    by_number: dict[int, WorkItem] = {}
    for item in items:
        old = by_number.get(item.number)
        if old is None or len(item.description) > len(old.description):
            by_number[item.number] = item
    return [by_number[n] for n in sorted(by_number)]


def _finish_item(item: WorkItem, buffer: list[str]) -> WorkItem | None:
    item.description = "\n".join(clean_description_lines(buffer)).strip()
    item.summary = make_summary(item.description, item.number)
    item.group = grouping_key(item)
    if not item.description.strip() or _is_heading_only(item.description):
        return None
    item.included = item.group not in AUTO_EXCLUDED_GROUPS
    return item


def _parse_columnar(text: str, project_number: str, start_item: int, end_item: int) -> list[WorkItem]:
    items: list[WorkItem] = []
    current: WorkItem | None = None
    buffer: list[str] = []
    columns: tuple[int, int, int, int] | None = None

    def flush() -> None:
        nonlocal current, buffer
        if current is not None:
            finished = _finish_item(current, buffer)
            if finished is not None:
                items.append(finished)
        current = None
        buffer = []

    for raw in text.splitlines():
        line = raw.rstrip("\n")
        header_match = re.search(r"\bItem\b\s+Shipowner No\.\s+Text\s+Status\s*$", line)
        if header_match:
            item_pos = line.index("Item")
            owner_pos = line.index("Shipowner", item_pos)
            text_pos = line.index("Text", owner_pos)
            status_pos = line.rindex("Status")
            columns = (item_pos, owner_pos, text_pos, status_pos)
            continue

        if columns is None:
            continue
        item_pos, owner_pos, text_pos, status_pos = columns
        padded = line + " " * max(0, status_pos + 1 - len(line))
        item_field = padded[item_pos:owner_pos].strip()
        owner_field = padded[owner_pos:text_pos].strip()
        text_field = padded[text_pos:status_pos].strip()
        status_field = padded[status_pos:].strip()

        if re.fullmatch(r"\d{4}", item_field):
            flush()
            number = int(item_field)
            if start_item <= number <= end_item:
                status = next((s for s in STATUS_VALUES if s.lower() == status_field.lower()), status_field)
                current = WorkItem(number=number, owner_no=owner_field, status=status, description="")
                if text_field:
                    buffer.append(text_field)
            continue

        if current is None:
            continue
        if text_field and not _is_page_noise(text_field, project_number) and not _is_layout_noise_fragment(text_field):
            buffer.append(text_field)

    flush()
    return items


def _parse_fallback(text: str, project_number: str, start_item: int, end_item: int) -> list[WorkItem]:
    """Used for PDFs that do not preserve the table columns in layout mode."""
    items: list[WorkItem] = []
    current: WorkItem | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal current, buffer
        if current is not None:
            finished = _finish_item(current, buffer)
            if finished is not None:
                items.append(finished)
        current = None
        buffer = []

    for raw in text.splitlines():
        line = raw.rstrip()
        header = _match_item_header(line)
        if header:
            flush()
            if start_item <= header[0] <= end_item:
                current = WorkItem(number=header[0], owner_no=header[1], status=header[2], description="")
            continue
        if current is not None and not _is_page_noise(line, project_number):
            buffer.append(line)
    flush()
    return items
