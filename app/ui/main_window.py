"""The main application window."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, QPoint, QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    APP_TITLE,
    APP_VERSION,
    MASTER_TEMPLATE,
    ProjectInfo,
    load_settings,
    save_settings,
)
from ..docx_export import compose_group_description, generate_docx
from ..grouping import apply_auto_grouping, apply_steel_auto_exclusions, group_items
from ..models import WorkItem
from ..pdf_parser import detect_project, extract_pdf_text, parse_work_items
from .assets import asset, icon
from .dialogs import EditSummaryDialog, SettingsDialog, WorkCategoryDialog
from .theme import SUCCESS, WARNING, build_stylesheet
from .widgets import BackgroundWidget, GroupCard, TitleBar, UploadDropFrame, add_shadow

GROUP_NAV_INDEX = 2


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(QIcon(asset("app_icon.png")))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.resize(1600, 920)
        self.setMinimumSize(1260, 760)

        self.items: list[WorkItem] = []
        self.source_path: Path | None = None
        self.last_output: Path | None = None
        self.info = load_settings()
        self.grouping_mode = "balanced"
        self.category_name = "Steel"
        self.range_start = 3000
        self.range_end = 3999
        self.selected_group_index = 0
        self._table_updating = False
        self._page_count = 0

        self._build_ui()
        self._apply_styles()
        self._update_file_card()
        self._update_report_groups()

    def _build_ui(self) -> None:
        # The shipyard photograph is the full-window background. Every UI surface floats above it.
        background = BackgroundWidget(asset("shipyard_background.jpg"))
        root_layout = QVBoxLayout(background)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(TitleBar(self))
        root_layout.addWidget(self._build_brand_header())

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(28, 10, 28, 10)
        body_layout.setSpacing(14)

        body_layout.addWidget(self._build_sidebar(), 0)
        body_layout.addWidget(self._build_center_panel(), 1)
        body_layout.addWidget(self._build_right_panel(), 0)

        root_layout.addWidget(body, 1)
        root_layout.addWidget(self._build_footer())
        self.setCentralWidget(background)

    def _build_brand_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("brandHeader")
        header.setMinimumHeight(108)
        header.setMaximumHeight(120)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(30, 8, 30, 4)
        layout.setSpacing(12)

        brand = QLabel()
        brand.setObjectName("brandLogo")
        brand_pixmap = QPixmap(asset("brand_logo_transparent.png"))
        brand.setPixmap(brand_pixmap.scaled(430, 116, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand.setMinimumWidth(440)
        layout.addWidget(brand)
        layout.addStretch(1)

        credit = QLabel(
            "Made by <span style='color:#47a8ff; font-weight:700;'>Aleksandar Chiplakovski</span> "
            "exclusively for ODD"
        )
        credit.setObjectName("creditLabel")
        credit.setTextFormat(Qt.RichText)
        credit.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(credit)
        return header

    def _build_sidebar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("glassPanel")
        frame.setFixedWidth(224)
        add_shadow(frame)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(9)

        buttons = [
            ("Dashboard", "home", self.show_dashboard),
            ("Import Work List", "upload", self.choose_pdf),
            (self._group_nav_label(), "group", self.open_group_items),
            ("Report Preview", "document", self.focus_preview),
            ("Generate Reports", "generate", self.generate_reports),
            ("Settings", "settings", self.open_settings),
        ]
        self.nav_buttons: list[QPushButton] = []
        for index, (label, icon_name, handler) in enumerate(buttons):
            btn = QPushButton(label)
            btn.setIcon(icon(icon_name))
            btn.setIconSize(QSize(24, 24))
            btn.setObjectName("navActive" if index == 0 else "navButton")
            btn.setMinimumHeight(49)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(handler)
            layout.addWidget(btn)
            self.nav_buttons.append(btn)
        layout.addStretch(1)

        status_card = QFrame()
        status_card.setObjectName("statusCard")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(13, 12, 13, 12)
        status_layout.addWidget(QLabel("Application Status"))
        self.ready_label = QLabel("●  Ready")
        self.ready_label.setObjectName("readyLabel")
        status_layout.addWidget(self.ready_label)
        version = QLabel(f"Version {APP_VERSION}")
        version.setObjectName("mutedLabel")
        status_layout.addSpacing(8)
        status_layout.addWidget(version)
        layout.addWidget(status_card)
        return frame

    def _group_nav_label(self) -> str:
        return f"Group Items {self.range_start}-{self.range_end}"

    def _build_center_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("glassPanel")
        add_shadow(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        list_icon = QLabel()
        list_icon.setPixmap(icon("document").pixmap(24, 24))
        title_row.addWidget(list_icon)
        title = QLabel("Work List Processing")
        title.setObjectName("sectionTitle")
        title_row.addWidget(title)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        upload_row = QHBoxLayout()
        upload_row.setSpacing(10)
        self.drop_zone = UploadDropFrame()
        self.drop_zone.setMinimumHeight(88)
        self.drop_zone.fileDropped.connect(self.set_pdf_path)
        self.drop_zone.browseRequested.connect(self.choose_pdf)
        upload_row.addWidget(self.drop_zone, 3)

        self.file_card = QFrame()
        self.file_card.setObjectName("fileCard")
        self.file_card.setMinimumHeight(88)
        file_layout = QHBoxLayout(self.file_card)
        file_layout.setContentsMargins(13, 10, 13, 10)
        pdf_icon = QLabel("PDF")
        pdf_icon.setObjectName("pdfBadge")
        pdf_icon.setAlignment(Qt.AlignCenter)
        pdf_icon.setFixedSize(42, 48)
        file_layout.addWidget(pdf_icon)
        file_text = QVBoxLayout()
        self.file_name_label = QLabel("No work list loaded")
        self.file_name_label.setObjectName("fileName")
        self.file_status_label = QLabel("Select a PDF work list")
        self.file_status_label.setObjectName("mutedLabel")
        self.file_meta_label = QLabel("Pages: —     Extracted: —")
        self.file_meta_label.setObjectName("mutedLabel")
        file_text.addWidget(self.file_name_label)
        file_text.addWidget(self.file_status_label)
        file_text.addWidget(self.file_meta_label)
        file_layout.addLayout(file_text, 1)
        replace = QPushButton("Replace File")
        replace.setObjectName("secondaryButton")
        replace.clicked.connect(self.choose_pdf)
        file_layout.addWidget(replace)
        upload_row.addWidget(self.file_card, 2)
        layout.addLayout(upload_row)

        fields = QFrame()
        fields.setObjectName("fieldsFrame")
        fields_layout = QVBoxLayout(fields)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_layout.setSpacing(6)
        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        self.project_name = self._field(row1, "Project Name")
        self.project_number = self._field(row1, "Project Number")
        self.ship_name = self._field(row1, "Ship Name")
        self.inspection_date = self._date_field()
        self._field_widget(row2, "Inspection Date", self.inspection_date)
        self.inspectors = self._field(row2, "Inspectors")
        self.inspectors.setText(self.info.inspector_names.replace("\n", "; "))
        self.work_range = QLineEdit(f"{self.category_name} · {self.range_start}–{self.range_end}")
        self.work_range.setReadOnly(True)
        self._field_widget(row2, "Work List Range", self.work_range)
        fields_layout.addLayout(row1)
        fields_layout.addLayout(row2)
        layout.addWidget(fields)

        self.tree = QTreeWidget()
        self.tree.setObjectName("workTree")
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(["", "Item No.", "Status", "Group", "Description"])
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_table_menu)
        self.tree.itemChanged.connect(self.table_item_changed)
        self.tree.itemDoubleClicked.connect(self.edit_selected_summary)
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.tree.setMinimumHeight(330)
        layout.addWidget(self.tree, 1)

        action_row = QHBoxLayout()
        self.analyze_button = QPushButton("Analyze Work List")
        self.analyze_button.setIcon(icon("search"))
        self.analyze_button.setObjectName("largeSecondary")
        self.analyze_button.clicked.connect(self.analyze_work_list)
        action_row.addWidget(self.analyze_button)
        self.generate_button = QPushButton("Generate DOCX Reports")
        self.generate_button.setIcon(icon("generate"))
        self.generate_button.setObjectName("largePrimary")
        self.generate_button.clicked.connect(self.generate_reports)
        action_row.addWidget(self.generate_button)
        self.open_folder_button = QPushButton("Open Output Folder")
        self.open_folder_button.setIcon(icon("folder"))
        self.open_folder_button.setObjectName("largeSecondary")
        self.open_folder_button.clicked.connect(self.open_output_folder)
        action_row.addWidget(self.open_folder_button)
        layout.addLayout(action_row)
        return panel

    def _date_field(self) -> QDateEdit:
        edit = QDateEdit()
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("yyyy-MM-dd")
        qdate = QDate.fromString(self.info.report_date or date.today().isoformat(), "yyyy-MM-dd")
        edit.setDate(qdate if qdate.isValid() else QDate.currentDate())
        return edit

    def _field(self, row: QHBoxLayout, label: str) -> QLineEdit:
        edit = QLineEdit()
        self._field_widget(row, label, edit)
        return edit

    def _field_widget(self, row: QHBoxLayout, label: str, widget: QWidget) -> None:
        wrap = QVBoxLayout()
        wrap.setSpacing(4)
        lab = QLabel(label)
        lab.setObjectName("fieldLabel")
        wrap.addWidget(lab)
        wrap.addWidget(widget)
        row.addLayout(wrap, 1)

    def _build_right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("glassPanel")
        panel.setFixedWidth(410)
        add_shadow(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        doc_icon = QLabel()
        doc_icon.setPixmap(icon("document").pixmap(24, 24))
        title_row.addWidget(doc_icon)
        title = QLabel("Combined Inspection Reports")
        title.setObjectName("sectionTitle")
        title_row.addWidget(title)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        self.group_scroll = QScrollArea()
        self.group_scroll.setObjectName("groupScroll")
        self.group_scroll.setWidgetResizable(True)
        self.group_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.group_container = QWidget()
        self.group_layout = QVBoxLayout(self.group_container)
        self.group_layout.setContentsMargins(0, 0, 0, 0)
        self.group_layout.setSpacing(7)
        self.group_layout.addStretch(1)
        self.group_scroll.setWidget(self.group_container)
        self.group_scroll.setMinimumHeight(285)
        layout.addWidget(self.group_scroll)

        preview_header = QFrame()
        preview_header.setObjectName("previewHeader")
        preview_header_layout = QHBoxLayout(preview_header)
        preview_header_layout.setContentsMargins(10, 8, 10, 8)
        word = QLabel("W")
        word.setObjectName("wordBadge")
        word.setAlignment(Qt.AlignCenter)
        word.setFixedSize(27, 27)
        preview_header_layout.addWidget(word)
        preview_texts = QVBoxLayout()
        ptitle = QLabel("Report Preview")
        ptitle.setObjectName("groupTitle")
        self.preview_file_label = QLabel("No report selected")
        self.preview_file_label.setObjectName("previewFile")
        preview_texts.addWidget(ptitle)
        preview_texts.addWidget(self.preview_file_label)
        preview_header_layout.addLayout(preview_texts)
        preview_header_layout.addStretch(1)
        layout.addWidget(preview_header)

        self.preview_image = QLabel()
        self.preview_image.setObjectName("previewImage")
        self.preview_image.setAlignment(Qt.AlignCenter)
        self.preview_image.setMinimumHeight(245)
        self.preview_image.setPixmap(
            QPixmap(asset("report_preview.png")).scaled(360, 245, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        layout.addWidget(self.preview_image, 1)

        self.open_preview_button = QPushButton("Open Preview")
        self.open_preview_button.setIcon(icon("open"))
        self.open_preview_button.setObjectName("largeSecondary")
        self.open_preview_button.clicked.connect(self.open_preview)
        layout.addWidget(self.open_preview_button)
        return panel

    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("footer")
        footer.setFixedHeight(48)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(24, 0, 24, 0)
        self.footer_status = QLabel("●  All systems operational")
        self.footer_status.setObjectName("footerReady")
        layout.addWidget(self.footer_status)
        layout.addStretch(1)
        self.output_folder_label = QLabel("Output Folder: —")
        self.output_folder_label.setObjectName("mutedLabel")
        layout.addWidget(self.output_folder_label)
        self.report_count_label = QLabel("0 reports ready")
        self.report_count_label.setObjectName("reportCount")
        layout.addSpacing(18)
        layout.addWidget(self.report_count_label)
        return footer

    def _apply_styles(self) -> None:
        self.setStyleSheet(build_stylesheet())

    def set_active_nav(self, index: int) -> None:
        for i, btn in enumerate(self.nav_buttons):
            btn.setObjectName("navActive" if i == index else "navButton")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def show_dashboard(self) -> None:
        self.set_active_nav(0)

    def open_group_items(self) -> None:
        self.set_active_nav(GROUP_NAV_INDEX)
        dialog = WorkCategoryDialog(self.category_name, self.range_start, self.range_end, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.category_name = dialog.category_name.text().strip()
        self.range_start = dialog.start_item.value()
        self.range_end = dialog.end_item.value()
        self.work_range.setText(f"{self.category_name} · {self.range_start}–{self.range_end}")
        self.nav_buttons[GROUP_NAV_INDEX].setText(self._group_nav_label())

        # Clear the previously displayed department, then re-read the same PDF if loaded.
        self.items = []
        self.tree.clear()
        self._update_report_groups()
        self._update_file_card()
        self.status_message(f"Selected {self.category_name} items {self.range_start}–{self.range_end}.")
        if self.source_path:
            self.analyze_work_list()

    def focus_preview(self) -> None:
        self.set_active_nav(3)
        self.open_preview_button.setFocus()

    def choose_pdf(self) -> None:
        self.set_active_nav(1)
        path, _ = QFileDialog.getOpenFileName(self, "Select work list", str(Path.home()), "PDF files (*.pdf);;All files (*.*)")
        if path:
            self.set_pdf_path(path)

    def set_pdf_path(self, path: str) -> None:
        self.source_path = Path(path)
        self._page_count = 0
        try:
            from pypdf import PdfReader

            self._page_count = len(PdfReader(path).pages)
        except Exception:
            pass
        self._update_file_card()
        self.status_message(f"Work list selected: {self.source_path.name}")

    def _update_file_card(self) -> None:
        if self.source_path and self.source_path.exists():
            self.file_name_label.setText(self.source_path.name)
            self.file_status_label.setText("✓ Loaded successfully")
            self.file_status_label.setStyleSheet(f"color: {SUCCESS};")
            extracted = len(self.items) if self.items else "—"
            pages = self._page_count or "—"
            self.file_meta_label.setText(f"Pages: {pages}     Extracted: {extracted} items")
        else:
            self.file_name_label.setText("No work list loaded")
            self.file_status_label.setText("Select a PDF work list")
            self.file_status_label.setStyleSheet("")
            self.file_meta_label.setText("Pages: —     Extracted: —")

    def analyze_work_list(self) -> None:
        if not self.source_path:
            self.choose_pdf()
            if not self.source_path:
                return
        try:
            text = extract_pdf_text(self.source_path)
            ship, project_number = detect_project(text, self.source_path)
            items = parse_work_items(text, project_number, self.range_start, self.range_end)
            if not items:
                raise ValueError(f"No {self.category_name} items {self.range_start}–{self.range_end} were found in this PDF.")
            apply_steel_auto_exclusions(items, self.range_start, self.range_end)
            apply_auto_grouping(items, self.grouping_mode)
            self.items = items
            self.project_name.setText(ship)
            self.ship_name.setText(ship)
            self.project_number.setText(project_number)
            self._populate_tree()
            self._update_file_card()
            self._update_report_groups()
            self.status_message(
                f"Loaded {len(items)} {self.category_name.lower()} items ({self.range_start}–{self.range_end}) from {self.source_path.name}."
            )
        except Exception as exc:
            self.status_message("Could not analyze the work list.", error=True)
            QMessageBox.critical(self, APP_TITLE, str(exc))

    def _populate_tree(self) -> None:
        self._table_updating = True
        self.tree.clear()
        grouped: dict[str, list[WorkItem]] = {}
        order: list[str] = []
        for item in self.items:
            key = item.group or f"ITEM {item.number}"
            if key not in grouped:
                grouped[key] = []
                order.append(key)
            grouped[key].append(item)

        for key in order:
            group_item = QTreeWidgetItem(self.tree)
            group_item.setText(0, f"▾  {key}")
            group_item.setFirstColumnSpanned(True)
            group_item.setExpanded(True)
            group_item.setBackground(0, QColor("#174a7e"))
            group_item.setForeground(0, QColor("#dcecff"))
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)
            for item in grouped[key]:
                child = QTreeWidgetItem(group_item)
                child.setData(0, Qt.UserRole, item.number)
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Checked if item.included else Qt.Unchecked)
                child.setText(1, str(item.number))
                child.setText(2, item.status)
                child.setText(3, item.group)
                child.setText(4, item.summary.replace("\n", " | "))
                if item.status.lower() in {"finished", "completed"}:
                    child.setForeground(2, QColor(SUCCESS))
                elif item.status.lower() == "in progress":
                    child.setForeground(2, QColor(WARNING))
                if not item.included:
                    for column in range(5):
                        child.setForeground(column, QColor("#7f91a7"))
        self._table_updating = False

    def table_item_changed(self, tree_item: QTreeWidgetItem, column: int) -> None:
        if self._table_updating or column != 0:
            return
        number = tree_item.data(0, Qt.UserRole)
        if not number:
            return
        item = self._item_by_number(int(number))
        if item:
            item.included = tree_item.checkState(0) == Qt.Checked
            self._update_report_groups()

    def selected_work_items(self) -> list[WorkItem]:
        selected: list[WorkItem] = []
        seen: set[int] = set()
        for tree_item in self.tree.selectedItems():
            number = tree_item.data(0, Qt.UserRole)
            if number and int(number) not in seen:
                item = self._item_by_number(int(number))
                if item:
                    selected.append(item)
                    seen.add(item.number)
        return selected

    def _item_by_number(self, number: int) -> WorkItem | None:
        return next((item for item in self.items if item.number == number), None)

    def show_table_menu(self, pos: QPoint) -> None:
        if not self.items:
            return
        menu = QMenu(self)
        include_action = QAction("Include selected", self)
        exclude_action = QAction("Exclude selected", self)
        merge_action = QAction("Combine selected litras into one report", self)
        new_group_action = QAction("Put selected in new report group", self)
        edit_action = QAction("Edit selected summary", self)
        include_action.triggered.connect(lambda: self.set_selected_included(True))
        exclude_action.triggered.connect(lambda: self.set_selected_included(False))
        merge_action.triggered.connect(self.merge_selected)
        new_group_action.triggered.connect(self.new_group_selected)
        edit_action.triggered.connect(self.edit_selected_summary)
        menu.addAction(include_action)
        menu.addAction(exclude_action)
        menu.addSeparator()
        menu.addAction(merge_action)
        menu.addAction(new_group_action)
        menu.addSeparator()
        menu.addAction(edit_action)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def set_selected_included(self, included: bool) -> None:
        selected = self.selected_work_items()
        if not selected:
            return
        for item in selected:
            item.included = included
        self._populate_tree()
        self._update_report_groups()

    def merge_selected(self) -> None:
        selected = self.selected_work_items()
        if len(selected) < 2:
            QMessageBox.information(self, APP_TITLE, "Select at least two work items.")
            return
        default = selected[0].group or f"COMBINED {selected[0].number}"
        name, ok = QInputDialog.getText(self, APP_TITLE, "Name for the combined report group:", QLineEdit.EchoMode.Normal, default)
        if ok and name.strip():
            for item in selected:
                item.group = name.strip()
                item.included = True
            self._populate_tree()
            self._update_report_groups()

    def new_group_selected(self) -> None:
        selected = self.selected_work_items()
        if not selected:
            return
        default = "ITEMS " + "/".join(str(item.number) for item in selected)
        name, ok = QInputDialog.getText(self, APP_TITLE, "Name for the new report group:", QLineEdit.EchoMode.Normal, default)
        if ok and name.strip():
            for item in selected:
                item.group = name.strip()
                item.included = True
            self._populate_tree()
            self._update_report_groups()

    def edit_selected_summary(self, *_args) -> None:
        selected = self.selected_work_items()
        if not selected:
            return
        item = selected[0]
        dialog = EditSummaryDialog(item, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item.summary = dialog.summary.toPlainText().strip()
            self._populate_tree()
            self._update_report_groups()

    def _current_info(self) -> ProjectInfo:
        inspector_lines = [part.strip() for part in self.inspectors.text().replace("\n", ";").split(";") if part.strip()]
        return ProjectInfo(
            project_name=self.project_name.text().strip() or self.ship_name.text().strip(),
            project_number=self.project_number.text().strip(),
            report_date=self.inspection_date.date().toString("yyyy-MM-dd"),
            inspection_company=self.info.inspection_company,
            inspector_names="\n".join(inspector_lines),
            supervisor_company=self.info.supervisor_company,
            supervisor_name=self.info.supervisor_name,
            only_finished=self.info.only_finished,
            inspection_method=self.info.inspection_method,
            completion_result=self.info.completion_result,
        )

    def _update_report_groups(self) -> None:
        while self.group_layout.count():
            item = self.group_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        groups = group_items(self.items, self.info.only_finished) if self.items else []
        if self.selected_group_index >= len(groups):
            self.selected_group_index = 0
        for index, group in enumerate(groups):
            name = group[0].group or f"ITEM {group[0].number}"
            jobs = " / ".join(str(item.number) for item in group)
            card = GroupCard(index, name, jobs, len(group), index == self.selected_group_index)
            card.clicked.connect(self.select_group)
            self.group_layout.addWidget(card)
        self.group_layout.addStretch(1)
        self.report_count_label.setText(f"{len(groups)} reports ready")
        self._update_preview(groups)

    def select_group(self, index: int) -> None:
        self.selected_group_index = index
        self._update_report_groups()

    def _update_preview(self, groups: list[list[WorkItem]]) -> None:
        if not groups:
            self.preview_file_label.setText("No report selected")
            return
        group = groups[self.selected_group_index]
        name = group[0].group or f"ITEM {group[0].number}"
        safe_name = name.replace("/", "-")
        self.preview_file_label.setText(f"{safe_name}.docx")
        preview_tip = (
            compose_group_description(group)
            + f"\n\nInspection method: {self.info.inspection_method}"
            + f"\nResults selection: {self.info.completion_result}"
        )
        self.preview_image.setToolTip(preview_tip)

    def open_settings(self) -> None:
        self.set_active_nav(5)
        dialog = SettingsDialog(self.info, self.grouping_mode, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.info.inspection_company = dialog.company.text().strip()
            inspector_lines = [part.strip() for part in dialog.inspectors.text().split(";") if part.strip()]
            self.info.inspector_names = "\n".join(inspector_lines)
            self.inspectors.setText("; ".join(inspector_lines))
            self.info.supervisor_company = dialog.supervisor_company.text().strip()
            self.info.supervisor_name = dialog.supervisor_name.text().strip()
            self.info.inspection_method = dialog.inspection_method.currentText()
            self.info.completion_result = dialog.completion_result.currentText()
            self.info.only_finished = dialog.only_finished.isChecked()
            self.grouping_mode = dialog.grouping.currentText()
            if self.items:
                apply_auto_grouping(self.items, self.grouping_mode)
                apply_steel_auto_exclusions(self.items, self.range_start, self.range_end)
                self._populate_tree()
            save_settings(self.info)
            self._update_report_groups()
            self.status_message("Settings saved.")

    def generate_reports(self) -> None:
        self.set_active_nav(4)
        if not self.items:
            QMessageBox.information(self, APP_TITLE, "Analyze a work list first.")
            return
        info = self._current_info()
        if not info.project_name or not info.project_number:
            QMessageBox.warning(self, APP_TITLE, "Project name and project number are required.")
            return
        default_name = f"{info.project_number}_{info.project_name}_{self.category_name}_Inspection_and_Test_Reports.docx".replace(" ", "_")
        start_dir = str(self.source_path.parent if self.source_path else Path.home())
        output, _ = QFileDialog.getSaveFileName(self, "Save inspection reports", str(Path(start_dir) / default_name), "Word document (*.docx)")
        if not output:
            return
        try:
            count = generate_docx(self.items, info, Path(output), MASTER_TEMPLATE)
            self.last_output = Path(output)
            self.output_folder_label.setText(f"Output Folder: {self.last_output.parent}")
            save_settings(info)
            self.status_message(f"Created {count} inspection report page(s).")
            self.report_count_label.setText(f"{count} reports ready")
            QMessageBox.information(self, APP_TITLE, f"Created {count} inspection report page(s):\n\n{output}")
            self._open_with_system_default(output)
        except Exception as exc:
            self.status_message("Could not generate the reports.", error=True)
            QMessageBox.critical(self, APP_TITLE, str(exc))

    def open_output_folder(self) -> None:
        target = self.last_output.parent if self.last_output else (self.source_path.parent if self.source_path else None)
        if target and target.exists():
            if not self._open_with_system_default(str(target)):
                QMessageBox.information(self, APP_TITLE, str(target))
        else:
            QMessageBox.information(self, APP_TITLE, "Generate a report first, or load a work list.")

    def open_preview(self) -> None:
        if self.last_output and self.last_output.exists():
            if self._open_with_system_default(str(self.last_output)):
                return
        QMessageBox.information(
            self, APP_TITLE, "The preview shows the original ODD report form. Generate a report to open the completed Word document."
        )

    @staticmethod
    def _open_with_system_default(path: str) -> bool:
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
            return True
        except Exception:
            return False

    def status_message(self, text: str, error: bool = False) -> None:
        self.footer_status.setText("●  " + text)
        self.footer_status.setStyleSheet(f"color: {WARNING if error else SUCCESS}; font-weight: 600;")
        self.ready_label.setText("●  Attention" if error else "●  Ready")
        self.ready_label.setStyleSheet(f"color: {WARNING if error else SUCCESS}; font-weight: 600;")
