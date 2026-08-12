"""Small reusable widgets used by the main window."""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .assets import asset, icon


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

        for label, handler in (("—", self.window_ref.showMinimized), ("□", self.toggle_maximize), ("×", self.window_ref.close)):
            btn = QPushButton(label)
            btn.setObjectName("windowControl")
            btn.setFixedSize(42, 30)
            btn.clicked.connect(handler)
            layout.addWidget(btn)

    def toggle_maximize(self) -> None:
        if self.window_ref.isMaximized():
            self.window_ref.showNormal()
        else:
            self.window_ref.showMaximized()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.window_ref.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self.drag_pos is not None and event.buttons() & Qt.LeftButton and not self.window_ref.isMaximized():
            self.window_ref.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self.drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()


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
    clicked = Signal(int)

    def __init__(self, index: int, title: str, jobs: str, count: int, selected: bool = False) -> None:
        super().__init__()
        self.index = index
        self.setObjectName("groupCardSelected" if selected else "groupCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(57)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 7, 10, 7)
        layout.setSpacing(10)
        doc = QLabel()
        doc.setPixmap(icon("document").pixmap(24, 24))
        layout.addWidget(doc)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        title_label = QLabel(title)
        title_label.setObjectName("groupTitle")
        jobs_label = QLabel(jobs)
        jobs_label.setObjectName("groupJobs")
        text_layout.addWidget(title_label)
        text_layout.addWidget(jobs_label)
        layout.addLayout(text_layout)
        layout.addStretch(1)
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
