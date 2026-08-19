"""An in-app PDF viewer for generated inspection reports, with print + print preview."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout

from ..config import APP_TITLE


class PdfViewerDialog(QDialog):
    """Reused across "Open" clicks (see MainWindow._open_report_pdf) rather than
    recreated each time - load_pdf() swaps in a new file. Non-modal: closing it just
    hides the window (default QDialog behavior), so the same instance is ready next time."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlag(Qt.Window, True)
        self.resize(950, 1000)
        self._document = QPdfDocument(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(12, 8, 12, 8)
        self._title_label = QLabel()
        self._title_label.setObjectName("sectionTitle")
        toolbar.addWidget(self._title_label, 1)
        print_button = QPushButton("Print...")
        print_button.setObjectName("secondaryButton")
        print_button.clicked.connect(self._print_document)
        toolbar.addWidget(print_button)
        layout.addLayout(toolbar)

        self._view = QPdfView(self)
        self._view.setDocument(self._document)
        self._view.setPageMode(QPdfView.PageMode.MultiPage)
        self._view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        layout.addWidget(self._view, 1)

    def load_pdf(self, path: Path) -> None:
        self.setWindowTitle(f"{path.name} - {APP_TITLE}")
        self._title_label.setText(path.name)
        self._document.load(str(path))

    def _print_document(self) -> None:
        if self._document.pageCount() < 1:
            QMessageBox.information(self, APP_TITLE, "Nothing to print yet.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(self._render_for_print)
        preview.exec()

    def _render_for_print(self, printer: QPrinter) -> None:
        painter = QPainter(printer)
        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        for page in range(self._document.pageCount()):
            if page > 0:
                printer.newPage()
            pt_size = self._document.pagePointSize(page)
            if pt_size.width() <= 0 or pt_size.height() <= 0:
                continue
            scale = min(page_rect.width() / pt_size.width(), page_rect.height() / pt_size.height())
            image_size = QSize(max(1, int(pt_size.width() * scale)), max(1, int(pt_size.height() * scale)))
            image = self._document.render(page, image_size)
            x = (page_rect.width() - image_size.width()) / 2
            y = (page_rect.height() - image_size.height()) / 2
            painter.drawImage(int(x), int(y), image)
        painter.end()
