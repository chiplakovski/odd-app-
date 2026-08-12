# ODD Inspection Report Generator

Desktop app that reads a shipyard PDF work list, groups the line items into
inspection sections, and generates Word (`.docx`) inspection reports from an
ODD master template.

## Project layout

```
app/
  config.py         paths, constants, persisted settings
  models.py         WorkItem data model
  pdf_parser.py      PDF text extraction + work-list parsing
  grouping.py         automatic grouping of items into report sections
  docx_export.py      Word report generation from the master template
  cli.py               command-line report generation (no GUI)
  main.py               GUI entry point
  ui/
    theme.py             colours + stylesheet
    assets.py            asset/icon path helpers
    widgets.py            background, title bar, drop zone, group card
    dialogs.py             settings, category picker, litra grouping, summary editor
    main_window.py          main window
  assets/                 images and icons
  templates/
    Inspection_Master_Template.docx
```

## Setup

1. Install Python 3.10 or newer.
2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\activate        (Windows)
   source .venv/bin/activate     (macOS/Linux)
   pip install -r requirements.txt
   ```

On Windows you can instead run `SETUP_SOURCE.cmd` once.

## Run

```
python -m app.main
```

On Windows, `RUN_FROM_SOURCE.cmd` launches the app after setup.

## Command-line report generation

```
python -m app.cli path/to/worklist.pdf path/to/output.docx --start-item 3000 --end-item 3999
```

## Templates

The report layout comes from `app/templates/Inspection_Master_Template.docx`.
Drop in a replacement file with the same name to change the report design,
or pass a different template path to `generate_docx()` / `--template`.
