"""Command-line entry point for generating reports without the GUI."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .config import MASTER_TEMPLATE, load_settings
from .docx_export import generate_docx
from .grouping import apply_auto_grouping, apply_steel_auto_exclusions
from .pdf_parser import detect_project, extract_pdf_text, parse_work_items


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate ODD inspection reports from a PDF work list.")
    parser.add_argument("input", help="Path to the source PDF work list")
    parser.add_argument("output", help="Path to save the generated .docx report")
    parser.add_argument("--start-item", type=int, default=3000)
    parser.add_argument("--end-item", type=int, default=3999)
    parser.add_argument("--grouping", choices=["none", "balanced", "maximum"], default="balanced")
    parser.add_argument("--exclude", nargs="*", default=[], help="Item numbers to exclude")
    parser.add_argument("--project-name")
    parser.add_argument("--project-number")
    parser.add_argument("--date")
    parser.add_argument("--include-in-progress", action="store_true")
    parser.add_argument("--template", type=Path, default=MASTER_TEMPLATE, help="Master .docx template to fill in")
    return parser


def run_cli(args: argparse.Namespace) -> int:
    source = Path(args.input).resolve()
    text = extract_pdf_text(source)
    name, number = detect_project(text, source)
    items = parse_work_items(text, number, args.start_item, args.end_item)
    apply_auto_grouping(items, args.grouping)
    apply_steel_auto_exclusions(items, args.start_item, args.end_item)
    excluded = {int(x) for x in (args.exclude or [])}
    for item in items:
        if item.number in excluded:
            item.included = False
    info = load_settings()
    info.project_name = args.project_name or name
    info.project_number = args.project_number or number
    info.report_date = args.date or date.today().isoformat()
    info.only_finished = not args.include_in_progress
    out = Path(args.output).resolve()
    count = generate_docx(items, info, out, master_template=Path(args.template))
    print(f"Created {count} inspection report page(s): {out}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
