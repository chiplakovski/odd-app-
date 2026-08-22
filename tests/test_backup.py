"""Tests for app/backup.py - export/import of all app data as a single zip file.

Uses a temporary directory in place of the real USER_DATA_DIR (via monkeypatch) so this
never touches a real installation's actual settings/history.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import app.backup as backup


def test_export_excludes_print_inbox_and_zips_everything_else(tmp_path, monkeypatch):
    user_data_dir = tmp_path / "user_data"
    inbox = user_data_dir / "PrintInbox"
    inbox.mkdir(parents=True)
    (user_data_dir / "settings.json").write_text('{"a": 1}', encoding="utf-8")
    (user_data_dir / "work_list_history.json").write_text("[]", encoding="utf-8")
    (inbox / "leftover.pdf").write_bytes(b"%PDF-fake")

    monkeypatch.setattr(backup, "USER_DATA_DIR", user_data_dir)
    monkeypatch.setattr(backup, "PRINT_INBOX_DIR", inbox)

    dest = tmp_path / "export.zip"
    count = backup.export_app_data(dest)

    assert count == 2
    with zipfile.ZipFile(dest) as zf:
        names = set(zf.namelist())
    assert names == {"settings.json", "work_list_history.json"}


def test_import_restores_files_and_returns_count(tmp_path, monkeypatch):
    export_dir = tmp_path / "export_source"
    export_dir.mkdir()
    (export_dir / "settings.json").write_text('{"a": 1}', encoding="utf-8")
    nested = export_dir / "ODD work" / "124-000" / "IRep"
    nested.mkdir(parents=True)
    (nested / "report.pdf").write_bytes(b"%PDF-fake")

    src_zip = tmp_path / "backup.zip"
    with zipfile.ZipFile(src_zip, "w") as zf:
        for path in export_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(export_dir))

    restore_dir = tmp_path / "restored_user_data"
    monkeypatch.setattr(backup, "USER_DATA_DIR", restore_dir)

    count = backup.import_app_data(src_zip)

    assert count == 2
    assert (restore_dir / "settings.json").read_text(encoding="utf-8") == '{"a": 1}'
    assert (restore_dir / "ODD work" / "124-000" / "IRep" / "report.pdf").read_bytes() == b"%PDF-fake"


def test_export_then_import_round_trip(tmp_path, monkeypatch):
    source_dir = tmp_path / "source_user_data"
    source_dir.mkdir()
    (source_dir / "settings.json").write_text('{"x": 42}', encoding="utf-8")

    monkeypatch.setattr(backup, "USER_DATA_DIR", source_dir)
    monkeypatch.setattr(backup, "PRINT_INBOX_DIR", source_dir / "PrintInbox")
    zip_path = tmp_path / "roundtrip.zip"
    backup.export_app_data(zip_path)

    restore_dir = tmp_path / "restored_user_data"
    monkeypatch.setattr(backup, "USER_DATA_DIR", restore_dir)
    backup.import_app_data(zip_path)

    assert (restore_dir / "settings.json").read_text(encoding="utf-8") == '{"x": 42}'
