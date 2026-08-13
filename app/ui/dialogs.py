"""Modal dialogs: settings, work category selection, litra grouping, summary editing, history."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import APP_TITLE, ProjectInfo, WORK_CATEGORY_PRESETS
from ..history import HistoryEntry, clear_history
from ..hotwork import HotWorkChecklist
from ..hotwork_export import default_location
from ..models import WorkItem
from .os_utils import open_with_system_default
from .theme import SUCCESS, WARNING


class SettingsDialog(QDialog):
    def __init__(self, info: ProjectInfo, grouping: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ODD Report Generator Settings")
        self.resize(650, 540)
        self.setObjectName("settingsDialog")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(14)
        self.company = QLineEdit(info.inspection_company)
        self.inspectors = QLineEdit(info.inspector_names.replace("\n", "; "))
        self.supervisor_company = QLineEdit(info.supervisor_company)
        self.supervisor_name = QLineEdit(info.supervisor_name)
        self.only_finished = QCheckBox("Only include Finished / Completed items")
        self.only_finished.setChecked(info.only_finished)
        self.grouping = QComboBox()
        self.grouping.addItems(["none", "balanced", "maximum"])
        self.grouping.setCurrentText(grouping)

        self.inspection_method = QComboBox()
        self.inspection_method.addItems(["Visual inspection", "Visual & NDT control"])
        self.inspection_method.setCurrentText(info.inspection_method or "Visual inspection")

        self.completion_result = QComboBox()
        self.completion_result.addItems([
            "Automatic (from work list)",
            "Final inspection",
            "Completed jobs",
            "Partially completed",
        ])
        self.completion_result.setCurrentText(info.completion_result or "Automatic (from work list)")

        form.addRow("Inspection company", self.company)
        form.addRow("Inspectors (; separated)", self.inspectors)
        form.addRow("Supervisor company", self.supervisor_company)
        form.addRow("Supervisor name", self.supervisor_name)
        form.addRow("Inspection and testing methods", self.inspection_method)
        form.addRow("Results and remarks", self.completion_result)
        form.addRow("Automatic grouping", self.grouping)
        form.addRow("", self.only_finished)
        layout.addLayout(form)
        note = QLabel("For the Steel range, items 3180, 3185 and 3195 are automatically excluded from the report set.")
        note.setWordWrap(True)
        note.setObjectName("mutedLabel")
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class WorkCategoryDialog(QDialog):
    """Choose the department/litra range to extract from the same work list."""

    def __init__(
        self,
        current_name: str,
        current_start: int,
        current_end: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Work Category / Litra Range")
        self.resize(560, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Select which department to read from the work list")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        note = QLabel(
            "The ranges do not overlap: Steel 3000–3999, Pipe 4000–4999, "
            "Mechanical 5000–5999 and Electrical 6000–6999. "
            "Use Custom for any other numbering system."
        )
        note.setWordWrap(True)
        note.setObjectName("mutedLabel")
        layout.addWidget(note)

        form = QFormLayout()
        form.setSpacing(12)
        self.preset = QComboBox()
        for name, start, end in WORK_CATEGORY_PRESETS:
            self.preset.addItem(f"{name} ({start}–{end})", (name, start, end))
        form.addRow("Department preset", self.preset)

        self.category_name = QLineEdit(current_name)
        form.addRow("Category name", self.category_name)

        range_row = QHBoxLayout()
        self.start_item = QSpinBox()
        self.start_item.setRange(0, 9999)
        self.start_item.setValue(current_start)
        self.end_item = QSpinBox()
        self.end_item.setRange(0, 9999)
        self.end_item.setValue(current_end)
        range_row.addWidget(QLabel("From"))
        range_row.addWidget(self.start_item, 1)
        range_row.addSpacing(12)
        range_row.addWidget(QLabel("To"))
        range_row.addWidget(self.end_item, 1)
        range_wrap = QWidget()
        range_wrap.setLayout(range_row)
        form.addRow("Litra / item range", range_wrap)
        layout.addLayout(form)

        self.preset.currentIndexChanged.connect(self.apply_preset)
        for index, (name, start, end) in enumerate(WORK_CATEGORY_PRESETS):
            if current_name.lower() == name.lower() and current_start == start and current_end == end:
                self.preset.setCurrentIndex(index)
                break
        else:
            self.preset.setCurrentIndex(len(WORK_CATEGORY_PRESETS) - 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        apply_button = QPushButton("Use This Category")
        apply_button.setObjectName("largePrimary")
        apply_button.clicked.connect(self.validate_and_accept)
        buttons.addButton(apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply_preset(self, _index: int = -1) -> None:
        data = self.preset.currentData()
        if not data:
            return
        name, start, end = data
        if name != "Custom":
            self.category_name.setText(name)
            self.start_item.setValue(start)
            self.end_item.setValue(end)
        elif not self.category_name.text().strip():
            self.category_name.setText("Custom")

    def validate_and_accept(self) -> None:
        name = self.category_name.text().strip()
        start = self.start_item.value()
        end = self.end_item.value()
        if not name:
            QMessageBox.warning(self, APP_TITLE, "Enter a category name.")
            return
        if start > end:
            QMessageBox.warning(self, APP_TITLE, "The From value must be lower than the To value.")
            return
        if end - start > 1999:
            QMessageBox.warning(self, APP_TITLE, "Select a range of maximum 2000 item numbers.")
            return
        self.accept()


class EditSummaryDialog(QDialog):
    def __init__(self, item: WorkItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Edit summary — Item {item.number}")
        self.resize(850, 620)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Original work-list text"))
        original = QTextEdit(item.description)
        original.setReadOnly(True)
        original.setMaximumHeight(220)
        layout.addWidget(original)
        layout.addWidget(QLabel("Text used in the inspection report"))
        self.summary = QTextEdit(item.summary)
        layout.addWidget(self.summary)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class GroupItemsDialog(QDialog):
    """Let the user group work items by clicking rows or typing litra numbers."""

    def __init__(
        self,
        items: list[WorkItem],
        preselected_numbers: list[int] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Combine Litras into One Report")
        self.resize(980, 700)
        self.items = items
        self._rows: dict[int, QTreeWidgetItem] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Select litras/items to combine into one inspection report")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        help_text = QLabel(
            "You can tick items in the list, or type item numbers below. "
            "Use comma, slash, space, or a range — for example: 3100, 3105, 3110-3113."
        )
        help_text.setWordWrap(True)
        help_text.setObjectName("mutedLabel")
        layout.addWidget(help_text)

        number_row = QHBoxLayout()
        self.number_input = QLineEdit()
        self.number_input.setPlaceholderText("Example: 3100 / 3105 / 3110 / 3112 / 3113")
        number_row.addWidget(self.number_input, 1)
        select_listed = QPushButton("Select Listed Items")
        select_listed.setObjectName("secondaryButton")
        select_listed.clicked.connect(self.select_listed_items)
        number_row.addWidget(select_listed)
        layout.addLayout(number_row)

        self.selection_note = QLabel("No typed item numbers applied yet.")
        self.selection_note.setObjectName("mutedLabel")
        layout.addWidget(self.selection_note)

        self.tree = QTreeWidget()
        self.tree.setObjectName("workTree")
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(["Select", "Item No.", "Status", "Current group", "Description"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.tree, 1)

        preselected = set(preselected_numbers or [])
        for item in self.items:
            row = QTreeWidgetItem(self.tree)
            row.setData(0, Qt.UserRole, item.number)
            row.setFlags(row.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            row.setCheckState(0, Qt.Checked if item.number in preselected else Qt.Unchecked)
            row.setText(1, str(item.number))
            row.setText(2, item.status)
            row.setText(3, item.group)
            row.setText(4, item.summary.replace("\n", " | "))
            if item.status.lower() in {"finished", "completed"}:
                row.setForeground(2, QColor(SUCCESS))
            elif item.status.lower() == "in progress":
                row.setForeground(2, QColor(WARNING))
            if not item.included:
                for column in range(5):
                    row.setForeground(column, QColor("#7f91a7"))
            self._rows[item.number] = row

        controls = QHBoxLayout()
        select_current = QPushButton("Use Highlighted Rows")
        select_current.setObjectName("secondaryButton")
        select_current.clicked.connect(self.use_highlighted_rows)
        controls.addWidget(select_current)
        select_included = QPushButton("Select Included Items")
        select_included.setObjectName("secondaryButton")
        select_included.clicked.connect(self.select_included_items)
        controls.addWidget(select_included)
        clear = QPushButton("Clear Selection")
        clear.setObjectName("secondaryButton")
        clear.clicked.connect(self.clear_selection)
        controls.addWidget(clear)
        controls.addStretch(1)
        layout.addLayout(controls)

        group_row = QHBoxLayout()
        group_label = QLabel("Report group name")
        group_label.setObjectName("fieldLabel")
        group_row.addWidget(group_label)
        self.group_name = QLineEdit()
        self.group_name.setPlaceholderText("Example: SWBT 1 Repairs")
        group_row.addWidget(self.group_name, 1)
        layout.addLayout(group_row)

        if preselected:
            selected_items = [item for item in self.items if item.number in preselected]
            current_groups = {item.group for item in selected_items if item.group}
            if len(current_groups) == 1:
                self.group_name.setText(next(iter(current_groups)))
            else:
                self.group_name.setText("COMBINED " + "/".join(str(n) for n in sorted(preselected)))
            self.selection_note.setText(f"{len(preselected)} item(s) selected from the main table.")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        apply_button = QPushButton("Create / Update Group")
        apply_button.setObjectName("largePrimary")
        apply_button.clicked.connect(self.validate_and_accept)
        buttons.addButton(apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.number_input.returnPressed.connect(self.select_listed_items)
        self.tree.itemDoubleClicked.connect(lambda item, _column: self._toggle_row(item))

    def _toggle_row(self, row: QTreeWidgetItem) -> None:
        row.setCheckState(0, Qt.Unchecked if row.checkState(0) == Qt.Checked else Qt.Checked)

    def checked_numbers(self) -> list[int]:
        numbers: list[int] = []
        for number, row in self._rows.items():
            if row.checkState(0) == Qt.Checked:
                numbers.append(number)
        return sorted(numbers)

    def parse_number_expression(self, text: str) -> set[int]:
        result: set[int] = set()
        for match in re.finditer(r"(?<!\d)(\d{4})(?:\s*-\s*(\d{4}))?(?!\d)", text):
            start = int(match.group(1))
            end_text = match.group(2)
            if end_text:
                end = int(end_text)
                low, high = sorted((start, end))
                result.update(range(low, high + 1))
            else:
                result.add(start)
        return result

    def select_listed_items(self) -> None:
        requested = self.parse_number_expression(self.number_input.text())
        if not requested:
            QMessageBox.information(self, APP_TITLE, "Enter one or more four-digit item numbers.")
            return
        existing = set(self._rows)
        matched = requested & existing
        missing = sorted(requested - existing)
        for number, row in self._rows.items():
            row.setCheckState(0, Qt.Checked if number in matched else Qt.Unchecked)
        message = f"Selected {len(matched)} matching item(s)."
        if missing:
            preview = ", ".join(str(n) for n in missing[:12])
            if len(missing) > 12:
                preview += ", ..."
            message += f" Not found in this work list: {preview}."
        self.selection_note.setText(message)
        if matched and not self.group_name.text().strip():
            self.group_name.setText("COMBINED " + "/".join(str(n) for n in sorted(matched)))

    def use_highlighted_rows(self) -> None:
        highlighted = {
            int(row.data(0, Qt.UserRole))
            for row in self.tree.selectedItems()
            if row.data(0, Qt.UserRole)
        }
        if not highlighted:
            QMessageBox.information(self, APP_TITLE, "Highlight one or more rows first.")
            return
        for number, row in self._rows.items():
            row.setCheckState(0, Qt.Checked if number in highlighted else Qt.Unchecked)
        self.number_input.setText(" / ".join(str(n) for n in sorted(highlighted)))
        self.selection_note.setText(f"Selected {len(highlighted)} highlighted item(s).")
        if not self.group_name.text().strip():
            self.group_name.setText("COMBINED " + "/".join(str(n) for n in sorted(highlighted)))

    def select_included_items(self) -> None:
        count = 0
        for item in self.items:
            checked = item.included
            self._rows[item.number].setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
            count += int(checked)
        self.selection_note.setText(f"Selected {count} currently included item(s).")

    def clear_selection(self) -> None:
        for row in self._rows.values():
            row.setCheckState(0, Qt.Unchecked)
        self.tree.clearSelection()
        self.number_input.clear()
        self.selection_note.setText("Selection cleared.")

    def validate_and_accept(self) -> None:
        selected = self.checked_numbers()
        if not selected:
            QMessageBox.warning(self, APP_TITLE, "Select or specify at least one work item.")
            return
        if not self.group_name.text().strip():
            QMessageBox.warning(self, APP_TITLE, "Enter a report group name.")
            self.group_name.setFocus()
            return
        self.accept()


class HistoryDialog(QDialog):
    """Shows previously processed work lists and lets the user reopen a generated report."""

    def __init__(self, entries: list[HistoryEntry], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Work List History")
        self.resize(1000, 560)
        self.entries = entries

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Previously processed work lists")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.table = QTreeWidget()
        self.table.setObjectName("workTree")
        self.table.setColumnCount(7)
        self.table.setHeaderLabels(["Date", "Type", "Work List", "Project", "Detail", "Count", "Output"])
        self.table.setRootIsDecorated(False)
        self.table.setAlternatingRowColors(False)
        header = self.table.header()
        for column in range(6):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        self._populate_table()
        layout.addWidget(self.table, 1)

        if not entries:
            empty = QLabel("No work orders, reports, or hot work permits processed yet.")
            empty.setObjectName("mutedLabel")
            layout.addWidget(empty)

        button_row = QHBoxLayout()
        open_button = QPushButton("Open Selected File")
        open_button.setObjectName("secondaryButton")
        open_button.clicked.connect(self._open_selected)
        button_row.addWidget(open_button)
        clear_button = QPushButton("Clear History")
        clear_button.setObjectName("secondaryButton")
        clear_button.clicked.connect(self._clear_history)
        button_row.addWidget(clear_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _populate_table(self) -> None:
        self.table.clear()
        for entry in self.entries:
            row = QTreeWidgetItem(self.table)
            row.setData(0, Qt.UserRole, entry.output_path)
            row.setText(0, entry.timestamp.replace("T", "  "))
            if entry.kind == "hotwork":
                row.setText(1, "Hot Work")
                row.setText(4, f"Item {entry.item_number} · {entry.date_from} to {entry.date_to}")
                row.setText(5, f"{entry.report_count} permit(s)")
            elif entry.kind == "workorder":
                row.setText(1, "Work Order")
                row.setText(4, f"{entry.category_name} {entry.range_start}-{entry.range_end}")
                row.setText(5, f"{entry.item_count} item(s)")
            else:
                row.setText(1, "Report")
                row.setText(4, f"{entry.category_name} {entry.range_start}-{entry.range_end}")
                row.setText(5, f"{entry.report_count} report(s)")
            row.setText(2, entry.source_name or "—")
            row.setText(3, f"{entry.project_name} ({entry.project_number})" if entry.project_name else "—")
            row.setText(6, entry.output_path or "—")

    def _open_selected(self) -> None:
        item = self.table.currentItem()
        if not item:
            QMessageBox.information(self, APP_TITLE, "Select a row first.")
            return
        path = item.data(0, Qt.UserRole)
        if not path or not Path(path).exists():
            QMessageBox.information(self, APP_TITLE, "The output file for this entry could not be found.")
            return
        open_with_system_default(path)

    def _clear_history(self) -> None:
        if not self.entries:
            return
        answer = QMessageBox.question(self, APP_TITLE, "Clear all work list history? This cannot be undone.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        clear_history()
        self.entries = []
        self._populate_table()


class HotWorkDialog(QDialog):
    """Configure and generate Hot Work Permits for one or more selected litras.

    One .docx is produced per item, containing one permit page per calendar day
    in the selected date range (the permit itself is only ever valid for a
    single day or shift, per the template).
    """

    def __init__(self, items: list[WorkItem], vessel: str, initial: HotWorkChecklist, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Generate Hot Work Permits")
        self.resize(760, 760)
        self.items = items
        self.vessel = vessel

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(10)

        title = QLabel("Generate Hot Work Permits")
        title.setObjectName("sectionTitle")
        outer.addWidget(title)

        if not items:
            warning = QLabel("Select one or more work items in the work list first, then reopen this dialog.")
            warning.setObjectName("mutedLabel")
            warning.setWordWrap(True)
            outer.addWidget(warning)

        selected_list = QListWidget()
        selected_list.setObjectName("workTree")
        selected_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        selected_list.setMaximumHeight(90)
        for item in items:
            QListWidgetItem(f"{item.number} · {default_location(item)}", selected_list)
        outer.addWidget(selected_list)

        scroll = QScrollArea()
        scroll.setObjectName("groupScroll")
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QVBoxLayout(content)
        form.setSpacing(10)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        # --- Date range ---
        form.addWidget(self._section_label("Permit valid dates (one permit page is generated per day)"))
        date_row = QHBoxLayout()
        today = QDate.currentDate()
        self.date_from = QDateEdit(today)
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("MMM d, yyyy")
        self.date_to = QDateEdit(today)
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("MMM d, yyyy")
        date_row.addWidget(QLabel("From"))
        date_row.addWidget(self.date_from, 1)
        date_row.addSpacing(12)
        date_row.addWidget(QLabel("To"))
        date_row.addWidget(self.date_to, 1)
        form.addLayout(date_row)

        # --- Location / logistics ---
        form.addWidget(self._section_label("Location"))
        logistics_row = QHBoxLayout()
        self.location = QLineEdit(initial.location)
        self.location.setPlaceholderText("Leave blank to use each item's own area")
        self.dock_quay = QLineEdit(initial.dock_quay)
        logistics_row.addWidget(self._labeled(self.location, "Location / Workplace override"), 2)
        logistics_row.addWidget(self._labeled(self.dock_quay, "Dock / Quay"), 1)
        form.addLayout(logistics_row)

        time_row = QHBoxLayout()
        self.start_time = QLineEdit(initial.start_time)
        self.stop_time = QLineEdit(initial.stop_time)
        time_row.addWidget(self._labeled(self.start_time, "Start Time (HH:MM)"), 1)
        time_row.addWidget(self._labeled(self.stop_time, "Stop Time (HH:MM)"), 1)
        form.addLayout(time_row)

        # --- Work method ---
        form.addWidget(self._section_label("Work method"))
        method_row = QHBoxLayout()
        self.welding = self._checkbox(method_row, "Welding", initial.welding)
        self.grinding = self._checkbox(method_row, "Grinding", initial.grinding)
        self.cutting = self._checkbox(method_row, "Cutting", initial.cutting)
        self.soldering = self._checkbox(method_row, "Soldering", initial.soldering)
        self.hot_air = self._checkbox(method_row, "Hot air", initial.hot_air)
        self.other = self._checkbox(method_row, "Other", initial.other)
        form.addLayout(method_row)
        self.other_text = QLineEdit(initial.other_text)
        self.other_text.setPlaceholderText("Specify other work method")
        form.addWidget(self.other_text)

        # --- MME fire hazard ---
        self.mme_yes, self.mme_no = self._yes_no_row(
            form, "Can the combination of Method, Material & Environment cause a fire hazard?", initial.mme_fire_hazard
        )

        # --- Numbered checklist ---
        form.addWidget(self._section_label("Checklist"))
        self.item_0 = self._checkbox_line(form, "0 — The permit issuer is appointed.", initial.item_0_issuer_appointed)
        self.item_1 = self._checkbox_line(
            form, "1 — The operator has a valid Swedish Hot Work Certificate.", initial.item_1_operator_certified
        )
        self.fire_watch_yes, self.fire_watch_no = self._yes_no_row(
            form, "2A — A competent Fire-Watch has been arranged.", initial.fire_watch_arranged
        )
        self.fire_watch_motivation = QLineEdit(initial.fire_watch_motivation)
        self.fire_watch_motivation.setPlaceholderText("If not arranged, specify the motivation / risk evaluation outcome")
        form.addWidget(self.fire_watch_motivation)
        self.item_2b = self._checkbox_line(
            form, "2B — Post-work monitoring (≥ 1 hour) has been arranged.", initial.item_2b_post_work_monitoring
        )
        self.item_3 = self._checkbox_line(
            form, "3 — Confined space permit stated, if applicable.", initial.item_3_confined_space_permit
        )
        self.item_4 = self._checkbox_line(form, "4 — The workplace is tidy and wetted down if necessary.", initial.item_4_workplace_tidy)
        self.item_5 = self._checkbox_line(
            form, "5 — Combustible material is removed, covered, or screened off.", initial.item_5_combustibles_removed
        )
        self.heat_structures_yes, self.heat_structures_no = self._yes_no_row(
            form, "6A — Heat-conducting / concealed combustible structures present.", initial.heat_conducting_structures_present
        )
        self.item_6b = self._checkbox_line(
            form, "6B — These are protected and accessible for extinguishing fire.", initial.item_6b_protected_accessible
        )
        self.openings_yes, self.openings_no = self._yes_no_row(
            form, "7A — Gaps, holes, penetrations or other openings present.", initial.openings_present
        )
        self.item_7b = self._checkbox_line(form, "7B — These openings are sealed or checked and protected.", initial.item_7b_openings_sealed)
        self.item_8 = self._checkbox_line(
            form, "8 — Sufficient fire-fighting equipment is available.", initial.item_8_firefighting_equipment
        )
        self.item_9 = self._checkbox_line(form, "9 — Welding equipment is free from defects.", initial.item_9_welding_equipment_ok)
        self.item_10 = self._checkbox_line(
            form, "10 — Emergency services / fire brigade can be alerted immediately.", initial.item_10_emergency_services_reachable
        )

        # --- Fire alarm disconnected ---
        form.addWidget(self._section_label("Automatic fire alarm / extinguishing system disconnected during the work"))
        alarm_row = QHBoxLayout()
        self.alarm_group = QButtonGroup(self)
        self.alarm_yes = QRadioButton("Yes")
        self.alarm_no = QRadioButton("No")
        self.alarm_na = QRadioButton("N/A")
        for button in (self.alarm_yes, self.alarm_no, self.alarm_na):
            self.alarm_group.addButton(button)
            alarm_row.addWidget(button)
        alarm_row.addStretch(1)
        {"yes": self.alarm_yes, "no": self.alarm_no, "na": self.alarm_na}.get(initial.fire_alarm_disconnected, self.alarm_yes).setChecked(True)
        form.addLayout(alarm_row)

        form.addStretch(1)

        note = QLabel("Settings are remembered per item, so reopening this dialog for the same litra recalls your last choices.")
        note.setObjectName("mutedLabel")
        note.setWordWrap(True)
        outer.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        generate_button = QPushButton("Generate Permits")
        generate_button.setObjectName("largePrimary")
        generate_button.setEnabled(bool(items))
        generate_button.clicked.connect(self.validate_and_accept)
        buttons.addButton(generate_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        label.setWordWrap(True)
        return label

    @staticmethod
    def _labeled(widget: QWidget, label_text: str) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        layout.addWidget(widget)
        return wrap

    @staticmethod
    def _checkbox(row: QHBoxLayout, text: str, checked: bool) -> QCheckBox:
        box = QCheckBox(text)
        box.setChecked(checked)
        row.addWidget(box)
        return box

    @staticmethod
    def _checkbox_line(form: QVBoxLayout, text: str, checked: bool) -> QCheckBox:
        box = QCheckBox(text)
        box.setChecked(checked)
        form.addWidget(box)
        return box

    @staticmethod
    def _yes_no_row(form: QVBoxLayout, label_text: str, yes_checked: bool) -> tuple[QRadioButton, QRadioButton]:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setWordWrap(True)
        row.addWidget(label, 1)
        yes = QRadioButton("Yes")
        no = QRadioButton("No")
        yes.setChecked(yes_checked)
        no.setChecked(not yes_checked)
        row.addWidget(yes)
        row.addWidget(no)
        form.addLayout(row)
        return yes, no

    def date_range(self) -> tuple[date, date]:
        return self.date_from.date().toPython(), self.date_to.date().toPython()

    def build_checklist(self) -> HotWorkChecklist:
        return HotWorkChecklist(
            welding=self.welding.isChecked(),
            grinding=self.grinding.isChecked(),
            cutting=self.cutting.isChecked(),
            soldering=self.soldering.isChecked(),
            hot_air=self.hot_air.isChecked(),
            other=self.other.isChecked(),
            other_text=self.other_text.text().strip(),
            mme_fire_hazard=self.mme_yes.isChecked(),
            item_0_issuer_appointed=self.item_0.isChecked(),
            item_1_operator_certified=self.item_1.isChecked(),
            fire_watch_arranged=self.fire_watch_yes.isChecked(),
            fire_watch_motivation=self.fire_watch_motivation.text().strip(),
            item_2b_post_work_monitoring=self.item_2b.isChecked(),
            item_3_confined_space_permit=self.item_3.isChecked(),
            item_4_workplace_tidy=self.item_4.isChecked(),
            item_5_combustibles_removed=self.item_5.isChecked(),
            heat_conducting_structures_present=self.heat_structures_yes.isChecked(),
            item_6b_protected_accessible=self.item_6b.isChecked(),
            openings_present=self.openings_yes.isChecked(),
            item_7b_openings_sealed=self.item_7b.isChecked(),
            item_8_firefighting_equipment=self.item_8.isChecked(),
            item_9_welding_equipment_ok=self.item_9.isChecked(),
            item_10_emergency_services_reachable=self.item_10.isChecked(),
            fire_alarm_disconnected="yes" if self.alarm_yes.isChecked() else "no" if self.alarm_no.isChecked() else "na",
            location=self.location.text().strip(),
            dock_quay=self.dock_quay.text().strip(),
            start_time=self.start_time.text().strip(),
            stop_time=self.stop_time.text().strip(),
        )

    def validate_and_accept(self) -> None:
        if not self.items:
            QMessageBox.warning(self, APP_TITLE, "Select one or more work items first.")
            return
        start, end = self.date_range()
        if not self.start_time.text().strip() or not self.stop_time.text().strip():
            QMessageBox.warning(self, APP_TITLE, "Enter both a start time and a stop time.")
            return
        self.accept()
