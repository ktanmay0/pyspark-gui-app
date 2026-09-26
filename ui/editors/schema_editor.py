"""Schema Editor — dialog for defining table schemas with CSV import."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from schema import (
    SPARK_TYPES,
    ColumnDef,
    SchemaRegistry,
    TableSchema,
    infer_schema_from_csv,
)


class _ColumnTable(QTableWidget):
    """Editable table for columns of a single table."""

    def __init__(self, columns: list[ColumnDef] | None = None):
        super().__init__()
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Column Name", "Type", "Nullable"])
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setDefaultSectionSize(130)
        for col in columns or []:
            self._add_row(col.name, col.data_type, col.nullable)

    def _add_row(
        self, name: str = "", dtype: str = "StringType", nullable: bool = True
    ):
        r = self.rowCount()
        self.insertRow(r)
        self.setItem(r, 0, QTableWidgetItem(name))
        tc = QComboBox()
        tc.addItems(SPARK_TYPES)
        tc.setCurrentText(dtype)
        self.setCellWidget(r, 1, tc)
        nc = QComboBox()
        nc.addItems(["True", "False"])
        nc.setCurrentText("True" if nullable else "False")
        self.setCellWidget(r, 2, nc)

    def add_column(self):
        self._add_row()

    def remove_selected(self):
        for r in sorted({i.row() for i in self.selectedIndexes()}, reverse=True):
            self.removeRow(r)

    def get_columns(self) -> list[ColumnDef]:
        result = []
        for r in range(self.rowCount()):
            name = self.item(r, 0)
            if not name or not name.text().strip():
                continue
            tc = self.cellWidget(r, 1)
            nc = self.cellWidget(r, 2)
            result.append(
                ColumnDef(
                    name=name.text().strip(),
                    data_type=tc.currentText() if tc else "StringType",
                    nullable=(nc.currentText() == "True") if nc else True,
                )
            )
        return result


class SchemaEditorDialog(QDialog):
    def __init__(self, registry: SchemaRegistry, parent=None):
        super().__init__(parent)
        self._registry = registry
        self.setWindowTitle("Schema Editor")
        self.resize(820, 600)
        self.setMinimumSize(680, 440)

        root = QVBoxLayout(self)

        # Toolbar
        tools = QHBoxLayout()
        add_tbl = QPushButton("+ Add Table")
        add_tbl.clicked.connect(self._add_table)
        tools.addWidget(add_tbl)
        remove_tbl = QPushButton("− Remove Table")
        remove_tbl.clicked.connect(self._remove_table)
        tools.addWidget(remove_tbl)
        tools.addStretch()
        import_csv = QPushButton("📥 Import from CSV…")
        import_csv.clicked.connect(self._import_csv)
        tools.addWidget(import_csv)
        root.addLayout(tools)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Table list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("<b>Tables</b>"))
        self._table_list = QListWidget()
        self._table_list.currentRowChanged.connect(self._on_table_selected)
        left_layout.addWidget(self._table_list)

        # Table name edit
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self._table_name = QLineEdit()
        self._table_name.setPlaceholderText("table_name")
        self._table_name.editingFinished.connect(self._on_name_changed)
        name_row.addWidget(self._table_name)
        left_layout.addLayout(name_row)
        splitter.addWidget(left)

        # Column table
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("<b>Columns</b>"))
        self._col_table = _ColumnTable()
        right_layout.addWidget(self._col_table)
        col_btns = QHBoxLayout()
        add_col = QPushButton("+ Add Column")
        add_col.clicked.connect(self._col_table.add_column)
        col_btns.addWidget(add_col)
        rem_col = QPushButton("− Remove Selected")
        rem_col.clicked.connect(self._col_table.remove_selected)
        col_btns.addWidget(rem_col)
        col_btns.addStretch()
        right_layout.addLayout(col_btns)
        splitter.addWidget(right)

        splitter.setSizes([220, 560])
        root.addWidget(splitter)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._rebuild_list()

    def _rebuild_list(self):
        self._table_list.blockSignals(True)
        self._table_list.clear()
        for t in self._registry.tables:
            self._table_list.addItem(t.table_name)
        self._table_list.blockSignals(False)

    def _on_table_selected(self, idx: int):
        if idx < 0:
            return
        t = self._registry.tables[idx]
        self._table_name.setText(t.table_name)
        self._col_table.clearContents()
        self._col_table.setRowCount(0)
        for col in t.columns:
            self._col_table._add_row(col.name, col.data_type, col.nullable)

    def _on_name_changed(self):
        idx = self._table_list.currentRow()
        if 0 <= idx < len(self._registry.tables):
            self._registry.tables[idx].table_name = self._table_name.text().strip()
            self._rebuild_list()
            self._table_list.setCurrentRow(idx)

    def _add_table(self):
        t = TableSchema(table_name=f"table_{len(self._registry.tables) + 1}")
        self._registry.add_table(t)
        self._rebuild_list()
        self._table_list.setCurrentRow(len(self._registry.tables) - 1)

    def _remove_table(self):
        idx = self._table_list.currentRow()
        if idx >= 0:
            self._registry.remove_table(idx)
            self._rebuild_list()

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV (*.csv)")
        if path:
            schema = infer_schema_from_csv(path)
            if schema:
                self._registry.add_table(schema)
                self._rebuild_list()
                self._table_list.setCurrentRow(len(self._registry.tables) - 1)
            else:
                QMessageBox.warning(self, "Error", "Could not read CSV schema.")

    def get_registry(self) -> SchemaRegistry:
        # Save current column edits before returning
        idx = self._table_list.currentRow()
        if 0 <= idx < len(self._registry.tables):
            self._registry.tables[idx].columns = self._col_table.get_columns()
        return self._registry
