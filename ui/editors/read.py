"""Editor for read_csv / read_parquet / read_json blocks."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

FORMATS = ["csv", "parquet", "json"]


class ReadEditor(QWidget):
    def __init__(self, params: dict | None = None, **kwargs):
        super().__init__()
        p = params or {}
        form = QFormLayout(self)
        form.setSpacing(10)

        path_row = QHBoxLayout()
        self.path = QLineEdit(p.get("path", ""))
        self.path.setPlaceholderText("/data/orders_2024.csv  – or click Browse…")
        path_row.addWidget(self.path)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        path_row.addWidget(browse)
        form.addRow("Path:", path_row)

        self.fmt = QComboBox()
        self.fmt.addItems(FORMATS)
        self.fmt.setCurrentText(p.get("format", "csv"))
        form.addRow("Format:", self.fmt)

        self.header = QCheckBox("First row is header")
        self.header.setChecked(p.get("header", True))
        form.addRow("", self.header)

        self.infer_schema = QCheckBox("Infer schema automatically")
        self.infer_schema.setChecked(p.get("infer_schema", True))
        form.addRow("", self.infer_schema)

        self.delimiter = QLineEdit(p.get("delimiter", ","))
        self.delimiter.setFixedWidth(60)
        self.delimiter.setPlaceholderText("e.g.,  ,  or  |  or  \\t")
        form.addRow("Delimiter:", self.delimiter)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Data File",
            "",
            "Data Files (*.csv *.parquet *.json);;All (*.*)",
        )
        if path:
            self.path.setText(path)

    def get_params(self) -> dict:
        return {
            "path": self.path.text().strip(),
            "format": self.fmt.currentText(),
            "header": self.header.isChecked(),
            "infer_schema": self.infer_schema.isChecked(),
            "delimiter": self.delimiter.text() or ",",
        }
