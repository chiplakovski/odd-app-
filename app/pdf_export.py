"""Converts a generated .docx report to PDF using Microsoft Word (COM automation).

Windows + Word only - the app's reports are meant to be viewed/printed from within the
app as PDF (see app/ui/pdf_viewer.py), and Word is used purely as the rendering engine
for that conversion since it's already on the machines this app runs on and reproduces
the template's exact layout/fonts, which a generic docx->pdf library can't guarantee.

Uses late-bound ("dynamic") COM dispatch (win32com.client.DispatchEx) rather than
win32com.client.gencache.EnsureDispatch deliberately: gencache writes a generated
wrapper module to a cache directory on first use, which behaves unpredictably from a
frozen PyInstaller executable. Dynamic dispatch has no such cache and needs no special
handling for a frozen build, at the minor cost of passing Word's documented constants
(e.g. wdFormatPDF) as plain numbers instead of named constants, and calling methods
positionally rather than by keyword (late-bound dispatch doesn't reliably support
Python-style keyword arguments for arbitrary COM methods).
"""
from __future__ import annotations

import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        import pythoncom
        import win32com.client

        _PYWIN32_AVAILABLE = True
    except ImportError:
        _PYWIN32_AVAILABLE = False
else:
    _PYWIN32_AVAILABLE = False

_WD_FORMAT_PDF = 17  # WdSaveFormat.wdFormatPDF


def convert_docx_to_pdf(docx_path: Path, pdf_path: Path) -> None:
    """Raises RuntimeError with a clear message on any failure - callers should catch
    this and fall back to keeping the .docx rather than losing the report entirely."""
    if not _PYWIN32_AVAILABLE:
        raise RuntimeError("PDF conversion requires Microsoft Word on Windows.")
    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(docx_path), False, True)  # ConfirmConversions, ReadOnly
        try:
            doc.SaveAs(str(pdf_path), _WD_FORMAT_PDF)
        finally:
            doc.Close(False)
    except Exception as exc:
        raise RuntimeError(f"Word could not convert the report to PDF: {exc}") from exc
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()
