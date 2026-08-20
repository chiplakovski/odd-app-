"""Small reusable widgets used by the main window."""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from .assets import asset, icon
from .theme import DANGER, SUCCESS


def add_shadow(widget: QWidget, blur: int = 24, opacity: int = 110, y: int = 6) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(0, 0, 0, opacity))
    widget.setGraphicsEffect(effect)


class _CoverImageWidget(QWidget):
    """Paints an image scaled to cover the widget's full area. The scaled pixmap is cached
    and only recomputed on resize, not on every paint (repaints are far more frequent than
    resizes, and SmoothPixmapTransform scaling isn't cheap)."""

    def __init__(self, image_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source = QPixmap(image_path)
        self._scaled = QPixmap()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        self._rescale()
        super().resizeEvent(event)

    def _rescale(self) -> None:
        if self._source.isNull() or self.size().isEmpty():
            self._scaled = QPixmap()
        else:
            self._scaled = self._source.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    def _paint_overlay(self, painter: QPainter) -> None:
        """Hook for subclasses to paint on top of the cover image."""

    def paintEvent(self, event) -> None:  # type: ignore[override]
        if self._scaled.isNull() and not self._source.isNull():
            self._rescale()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if not self._scaled.isNull():
            x = (self.width() - self._scaled.width()) // 2
            y = (self.height() - self._scaled.height()) // 2
            painter.drawPixmap(x, y, self._scaled)
        self._paint_overlay(painter)
        super().paintEvent(event)


class BackgroundWidget(_CoverImageWidget):
    """Full-window cover-fit background photo with a dark-blue grade for text readability."""

    def __init__(self, image_path: str, parent: QWidget | None = None) -> None:
        super().__init__(image_path, parent)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def _paint_overlay(self, painter: QPainter) -> None:
        # A restrained dark-blue grade keeps text readable without hiding the background.
        painter.fillRect(self.rect(), QColor(4, 19, 36, 46))


class BannerWidget(_CoverImageWidget):
    """A cover-fit image strip, used for the full-width brand header banner."""


class TitleBar(QFrame):
    def __init__(self, window: QMainWindow) -> None:
        super().__init__(window)
        self.window_ref = window
        self.drag_pos: QPoint | None = None
        self.setObjectName("titleBar")
        self.setFixedHeight(38)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 6, 0)
        layout.setSpacing(8)

        app_icon = QLabel()
        app_icon.setPixmap(QPixmap(asset("app_icon.png")).scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(app_icon)

        title = QLabel("ODD Inspection Report Generator")
        title.setObjectName("windowTitle")
        layout.addWidget(title)
        layout.addStretch(1)

        for label, handler in (
            ("—", self.window_ref.showMinimized),
            ("□", self.window_ref.toggle_maximize_state),
            ("×", self.window_ref.close),
        ):
            btn = QPushButton(label)
            btn.setObjectName("windowControl")
            btn.setFixedSize(42, 30)
            btn.clicked.connect(handler)
            layout.addWidget(btn)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.window_ref.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self.drag_pos is not None and event.buttons() & Qt.LeftButton and not self.window_ref.is_pseudo_maximized():
            self.window_ref.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self.drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.window_ref.toggle_maximize_state()


class UploadDropFrame(QFrame):
    fileDropped = Signal(str)
    browseRequested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 16, 22, 16)
        layout.setSpacing(15)
        cloud = QLabel()
        cloud.setPixmap(icon("cloud").pixmap(46, 46))
        layout.addWidget(cloud)
        txt = QVBoxLayout()
        title = QLabel("Drag & drop PDF work list here")
        title.setObjectName("dropTitle")
        subtitle = QLabel("or click to browse")
        subtitle.setObjectName("mutedLabel")
        txt.addWidget(title)
        txt.addWidget(subtitle)
        layout.addLayout(txt)
        layout.addStretch(1)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.browseRequested.emit()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        urls = event.mimeData().urls()
        if urls and urls[0].toLocalFile().lower().endswith(".pdf"):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith(".pdf"):
                self.fileDropped.emit(path)
                event.acceptProposedAction()


class ReportFileRow(QFrame):
    """A row in the generated-reports file list: filename + Open/Delete actions."""

    openRequested = Signal()
    deleteRequested = Signal()

    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__()
        self.setObjectName("groupCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        badge = QLabel("PDF")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(36, 18)
        badge.setStyleSheet(
            f"background: {SUCCESS}; color: #0a1420; border-radius: 5px; font-weight: 700; font-size: 8px;"
        )
        layout.addWidget(badge, 0, Qt.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        title_label = QLabel(self._wrappable(title))
        title_label.setObjectName("groupTitle")
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-size: 10px;")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("groupJobs")
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet("font-size: 9px;")
        text_layout.addWidget(title_label)
        text_layout.addWidget(subtitle_label)
        layout.addLayout(text_layout, 1)

        # Stacked rather than side-by-side: this frees the title column from having to
        # share width with two buttons, which is what wrapping the full (long,
        # underscore-separated) filename above actually needs room for.
        # Minimum, not fixed, width: a fixed pixel budget sized against this sandbox's
        # font metrics still clipped "Delete" under Windows' actual font rendering -
        # a minimum lets Qt's own size hint (which always fits the button's text) win
        # whenever it needs more room, while still keeping Open/Delete the same width.
        button_layout = QVBoxLayout()
        button_layout.setSpacing(4)
        open_button = QPushButton("Open")
        open_button.setObjectName("secondaryButton")
        open_button.setMinimumWidth(70)
        open_button.clicked.connect(self.openRequested.emit)
        button_layout.addWidget(open_button)

        delete_button = QPushButton("Delete")
        delete_button.setObjectName("secondaryButton")
        delete_button.setMinimumWidth(70)
        delete_button.setStyleSheet(f"color: {DANGER};")
        delete_button.clicked.connect(self.deleteRequested.emit)
        button_layout.addWidget(delete_button)
        layout.addLayout(button_layout)

    @staticmethod
    def _wrappable(text: str) -> str:
        """Insert a zero-width space after every underscore/hyphen so Qt's word-wrap
        (which only breaks at spaces) has somewhere to break - report/permit filenames
        are long and underscore-separated with no natural break points otherwise, which
        without this makes the label report its unbroken width as its minimum size and
        pushes the row wider than the fixed-width panel it lives in."""
        zwsp = chr(0x200B)
        return text.replace("_", "_" + zwsp).replace("-", "-" + zwsp)


class ActivityRow(QFrame):
    """A compact row in the Work Order History list: a kind badge, title/subtitle, and a
    Delete button (the row itself is informational, not clickable to open - deleting is
    the only action this list offers, since re-loading a work order is done by dropping
    the PDF in again rather than reopening a history entry)."""

    deleteRequested = Signal()

    def __init__(self, kind_label: str, kind_color: str, title: str, subtitle: str) -> None:
        super().__init__()
        self.setObjectName("groupCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        badge = QLabel(kind_label)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(76, 20)
        badge.setStyleSheet(
            f"background: {kind_color}; color: #0a1420; border-radius: 5px; font-weight: 700; font-size: 9px;"
        )
        layout.addWidget(badge)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        title_label = QLabel(title)
        title_label.setObjectName("groupTitle")
        title_label.setWordWrap(True)
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("groupJobs")
        subtitle_label.setWordWrap(True)
        text_layout.addWidget(title_label)
        text_layout.addWidget(subtitle_label)
        layout.addLayout(text_layout, 1)

        delete_button = QPushButton("Delete")
        delete_button.setObjectName("secondaryButton")
        delete_button.setMinimumWidth(70)
        delete_button.setStyleSheet(f"color: {DANGER};")
        delete_button.clicked.connect(self.deleteRequested.emit)
        layout.addWidget(delete_button)


class StatusBadgeDelegate(QStyledItemDelegate):
    """Paints INCLUDED / EXCLUDED cells in a given tree column as a rounded pill."""

    def __init__(self, column: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.column = column

    def paint(self, painter: QPainter, option, index) -> None:  # type: ignore[override]
        text = index.data(Qt.DisplayRole)
        if index.column() != self.column or text not in ("INCLUDED", "EXCLUDED"):
            super().paint(painter, option, index)
            return
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        background = QColor(SUCCESS) if text == "INCLUDED" else QColor(DANGER)
        rect = option.rect.adjusted(6, 6, -6, -6)
        painter.setPen(Qt.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(QColor("#0a1420"))
        font = QFont(option.font)
        font.setBold(True)
        font.setPointSize(max(7, option.font.pointSize()))
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, text)
        painter.restore()
