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


class BackgroundWidget(QWidget):
    def __init__(self, image_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap = QPixmap(image_path)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if not self._pixmap.isNull():
            # Cover the complete application window while keeping the shipyard image proportions.
            scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        # A restrained dark-blue grade keeps text readable without hiding the background.
        painter.fillRect(self.rect(), QColor(4, 19, 36, 46))
        super().paintEvent(event)


class BannerWidget(QWidget):
    """A cover-fit image strip, used for the full-width brand header banner."""

    def __init__(self, image_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap = QPixmap(image_path)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if not self._pixmap.isNull():
            scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        super().paintEvent(event)


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


class GroupCard(QFrame):
    """A compact row for one report group: name + item count. Click to jump to
    that group's rows in the main work list table."""

    clicked = Signal(int)

    def __init__(self, index: int, title: str, count: int, selected: bool = False) -> None:
        super().__init__()
        self.index = index
        self.setObjectName("groupCardSelected" if selected else "groupCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(38)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 10, 4)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("groupTitle")
        layout.addWidget(title_label, 1)
        badge = QLabel(str(count))
        badge.setObjectName("countBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(26, 26)
        layout.addWidget(badge)
        arrow = QLabel("›")
        arrow.setObjectName("chevron")
        layout.addWidget(arrow)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)


class ActivityRow(QFrame):
    """A compact row in the Recent Activity list: a kind badge, title/subtitle, and an Open button."""

    openRequested = Signal()

    def __init__(self, kind_label: str, kind_color: str, title: str, subtitle: str) -> None:
        super().__init__()
        self.setObjectName("groupCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        badge = QLabel(kind_label)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(64, 20)
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

        open_button = QPushButton("Open")
        open_button.setObjectName("secondaryButton")
        open_button.setFixedWidth(66)
        open_button.clicked.connect(self.openRequested.emit)
        layout.addWidget(open_button)


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
