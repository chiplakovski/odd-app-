"""Modal dialogs: settings, work category selection, litra grouping, summary editing, history."""
from __future__ import annotations

import zipfile
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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

from ..backup import export_app_data, import_app_data
from ..config import APP_TITLE, ProjectInfo, WORK_CATEGORY_PRESETS
from ..history import HistoryEntry, clear_history
from ..hotwork import HotWorkChecklist
from ..hotwork_export import default_location
from ..models import WorkItem
from .os_utils import open_with_system_default


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

        backup_row = QHBoxLayout()
        export_button = QPushButton("Export App Data...")
        export_button.setObjectName("secondaryButton")
        export_button.clicked.connect(self._export_app_data)
        backup_row.addWidget(export_button)
        import_button = QPushButton("Import App Data...")
        import_button.setObjectName("secondaryButton")
        import_button.clicked.connect(self._import_app_data)
        backup_row.addWidget(import_button)
        backup_row.addStretch(1)
        layout.addLayout(backup_row)
        backup_note = QLabel(
            "Export saves all settings, work order/report/hot work history, hot work "
            "checklists, and generated project files to one zip file - useful before "
            "reinstalling or moving to a new computer. Import restores from a previously "
            "exported zip (restart the app afterwards)."
        )
        backup_note.setWordWrap(True)
        backup_note.setObjectName("mutedLabel")
        layout.addWidget(backup_note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _export_app_data(self) -> None:
        default_name = f"ODD_App_Data_Backup_{date.today().isoformat()}.zip"
        path, _ = QFileDialog.getSaveFileName(self, "Export App Data", default_name, "Zip files (*.zip)")
        if not path:
            return
        if not path.lower().endswith(".zip"):
            path += ".zip"
        try:
            count = export_app_data(Path(path))
        except OSError as exc:
            QMessageBox.critical(self, APP_TITLE, f"Could not export app data:\n\n{exc}")
            return
        QMessageBox.information(self, APP_TITLE, f"Exported {count} file(s) to:\n\n{path}")

    def _import_app_data(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import App Data", "", "Zip files (*.zip)")
        if not path:
            return
        reply = QMessageBox.question(
            self, APP_TITLE,
            "Importing will overwrite any existing settings, history, and project files "
            "that also exist in this backup. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            count = import_app_data(Path(path))
        except (OSError, zipfile.BadZipFile) as exc:
            QMessageBox.critical(self, APP_TITLE, f"Could not import app data:\n\n{exc}")
            return
        QMessageBox.information(
            self, APP_TITLE,
            f"Imported {count} file(s) from:\n\n{path}\n\nRestart the app for all changes to take effect.",
        )


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


class HistoryDialog(QDialog):
    """Shows previously processed work lists and lets the user reopen a generated report."""

    def __init__(self, entries: list[HistoryEntry], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Work List History")
        self.resize(1000, 560)
        self.entries = entries
        self.load_requested_path: str | None = None

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
        entry = self.entries[self.table.indexOfTopLevelItem(item)]
        if entry.kind == "workorder":
            box = QMessageBox(self)
            box.setWindowTitle(APP_TITLE)
            box.setText(
                f'"{entry.source_name or Path(path).name}" is a work order\'s source PDF.\n\n'
                "Load it back into the program, or just open the file?"
            )
            load_button = box.addButton("Load into Program", QMessageBox.ButtonRole.AcceptRole)
            open_button = box.addButton("Open File", QMessageBox.ButtonRole.ActionRole)
            box.addButton(QMessageBox.StandardButton.Cancel)
            box.exec()
            clicked = box.clickedButton()
            if clicked is load_button:
                self.load_requested_path = path
                self.accept()
                return
            if clicked is not open_button:
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

    def __init__(
        self,
        items: list[WorkItem],
        vessel: str,
        initial: HotWorkChecklist,
        initial_locations: dict[int, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Generate Hot Work Permits")
        self.resize(760, 760)
        self.items = items
        self.vessel = vessel
        self._location_edits: dict[int, QLineEdit] = {}

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

        outer.addWidget(self._section_label(
            "Location for each item (required - a permit isn't generated for an item left "
            "blank). Pre-filled from the item's own text - add to it if needed, e.g. "
            "\"...- main deck cargo hold 1,2,3\""
        ))
        items_container = QWidget()
        items_layout = QVBoxLayout(items_container)
        items_layout.setContentsMargins(0, 0, 0, 0)
        items_layout.setSpacing(6)
        for item in items:
            row = QHBoxLayout()
            number_label = QLabel(str(item.number))
            number_label.setObjectName("groupTitle")
            number_label.setFixedWidth(50)
            row.addWidget(number_label)
            # Pre-filled as real (not placeholder) text: "<item> - <short description>", so
            # it's already a valid location on its own and the user can just click at the
            # end and add to it (e.g. "...- main deck cargo hold 1,2,3") instead of retyping
            # the whole thing from scratch.
            default_text = f"{item.number} - {default_location(item)}"
            edit = QLineEdit(initial_locations.get(item.number, "") or default_text)
            row.addWidget(edit, 1)
            self._location_edits[item.number] = edit
            items_layout.addLayout(row)
        items_scroll = QScrollArea()
        items_scroll.setObjectName("groupScroll")
        items_scroll.setWidgetResizable(True)
        items_scroll.setWidget(items_container)
        items_scroll.setMaximumHeight(140)
        outer.addWidget(items_scroll)

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

        # --- Dock / Quay (shared across all items in this batch; per-item Location is above) ---
        self.dock_quay = QLineEdit(initial.dock_quay)
        form.addWidget(self._labeled(self.dock_quay, "Dock / Quay"))

        form.addWidget(self._section_label("Shift (select both to get a separate permit file for each)"))
        shift_row = QHBoxLayout()
        self.day_shift = QCheckBox("Day shift (07:00 – 19:00)")
        self.night_shift = QCheckBox("Night shift (19:00 – 07:00)")
        # A saved item defaults to day shift unless it was explicitly saved as night shift.
        if (initial.start_time, initial.stop_time) == ("19:00", "07:00"):
            self.night_shift.setChecked(True)
        else:
            self.day_shift.setChecked(True)
        shift_row.addWidget(self.day_shift)
        shift_row.addWidget(self.night_shift)
        shift_row.addStretch(1)
        form.addLayout(shift_row)

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

    def _yes_no_row(self, form: QVBoxLayout, label_text: str, yes_checked: bool) -> tuple[QRadioButton, QRadioButton]:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setWordWrap(True)
        row.addWidget(label, 1)
        yes = QRadioButton("Yes")
        no = QRadioButton("No")
        # Each Yes/No pair needs its own group - QRadioButton siblings under the same
        # parent widget are mutually exclusive by default, so without this, checking
        # "Yes" on one question (e.g. MME fire hazard) was un-checking "Yes" on an
        # unrelated question (e.g. the Fire-Watch arranged) sharing this dialog's content
        # widget as their common parent.
        group = QButtonGroup(self)
        group.addButton(yes)
        group.addButton(no)
        yes.setChecked(yes_checked)
        no.setChecked(not yes_checked)
        row.addWidget(yes)
        row.addWidget(no)
        form.addLayout(row)
        return yes, no

    def date_range(self) -> tuple[date, date]:
        return self.date_from.date().toPython(), self.date_to.date().toPython()

    def selected_shifts(self) -> list[tuple[str, str, str]]:
        """(label, start_time, stop_time) for each checked shift, Day first."""
        shifts = []
        if self.day_shift.isChecked():
            shifts.append(("Day", "07:00", "19:00"))
        if self.night_shift.isChecked():
            shifts.append(("Night", "19:00", "07:00"))
        return shifts

    def location_for(self, item_number: int) -> str:
        edit = self._location_edits.get(item_number)
        return edit.text().strip() if edit else ""

    def build_checklist(self, start_time: str, stop_time: str, location: str) -> HotWorkChecklist:
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
            location=location,
            dock_quay=self.dock_quay.text().strip(),
            start_time=start_time,
            stop_time=stop_time,
        )

    def validate_and_accept(self) -> None:
        if not self.items:
            QMessageBox.warning(self, APP_TITLE, "Select one or more work items first.")
            return
        if not self.selected_shifts():
            QMessageBox.warning(self, APP_TITLE, "Select at least one shift.")
            return
        missing = [str(number) for number, edit in self._location_edits.items() if not edit.text().strip()]
        if missing:
            QMessageBox.warning(
                self, APP_TITLE,
                "Enter a location for every item before generating permits - no permit is "
                "created for an item left blank. Missing for item(s): " + ", ".join(missing),
            )
            return
        self.accept()
