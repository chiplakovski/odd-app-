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
  history.py           persisted history of processed work lists
  cli.py                 command-line report generation (no GUI)
  main.py                 GUI entry point
  ui/
    theme.py                colours + stylesheet
    assets.py               asset/icon path helpers
    os_utils.py              "open with system default app" helper
    widgets.py                background, title bar, drop zone, group card
    dialogs.py                 settings, category picker, litra grouping,
                                 summary editor, work list history
    main_window.py               main window
  assets/                 images, icons, app_icon.ico
  templates/
    Inspection_Master_Template.docx
launcher.py         standalone entry point used by the packaged build
packaging/
  build.spec         PyInstaller build spec
  installer.iss        Inno Setup installer script
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

## Work list history

Every time "Generate DOCX Reports" completes, an entry (source PDF, project,
category/range, item counts, and the generated `.docx` path) is appended to
`work_list_history.json` next to `settings.json` in the app's per-user data
folder. Open it from the **History** item in the sidebar to browse past runs
and reopen a previously generated report.

## Building a Windows installer (desktop icon)

Running from source (`RUN_FROM_SOURCE.cmd`) is fine for development, but it
doesn't give you a Start Menu entry or a desktop icon. To build a real
installer:

**Option A — GitHub Actions (no local setup required).** Push a tag like
`v1.0.0`, or run the "Build Windows Installer" workflow manually from the
Actions tab. It builds the app on a Windows runner and uploads
`ODD_Inspection_Report_Generator_Setup.exe` as a workflow artifact (and
attaches it to the GitHub Release for tag pushes).

**Option B — build locally on Windows:**
1. Run `SETUP_SOURCE.cmd` once (if you haven't already).
2. Install [Inno Setup](https://jrsoftware.org/isinfo.php) (free) if you want
   a real installer, not just the raw build.
3. Run `BUILD_INSTALLER.cmd`. This runs PyInstaller (`packaging/build.spec`)
   to produce `dist/ODD Inspection Report Generator/`, then compiles
   `packaging/installer.iss` with Inno Setup into
   `packaging/Output/ODD_Inspection_Report_Generator_Setup.exe`.

Either way, running the resulting `Setup.exe` installs the app under
`Program Files`, adds a Start Menu entry, and offers a desktop icon
(checked by default) that launches the app directly — no Python or venv
required on the target machine.
