"""Editor for write_csv / write_parquet blocks."""

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

WRITE_MODES = ["overwrite", "append", "ignore", "error"]
WRITE_FORMATS = ["csv", "parquet"]


class WriteEditor(QWidget):
    def __init__(self, params: dict | None = None, **kwargs):
        super().__init__()
        p = params or {}
        form = QFormLayout(self)
        form.setSpacing(10)

        path_row = QHBoxLayout()
        self.path = QLineEdit(p.get("path", ""))
        self.path.setPlaceholderText("/data/output/analysis_results  – or pick folder…")
        path_row.addWidget(self.path)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        path_row.addWidget(browse)
        form.addRow("Path:", path_row)

        self.fmt = QComboBox()
        self.fmt.addItems(WRITE_FORMATS)
        self.fmt.setCurrentText(p.get("format", "parquet"))
        form.addRow("Format:", self.fmt)

        self.mode = QComboBox()
        self.mode.addItems(WRITE_MODES)
        self.mode.setCurrentText(p.get("mode", "overwrite"))
        form.addRow("Mode:", self.mode)

        self.header = QCheckBox("Include header row (CSV only)")
        self.header.setChecked(p.get("header", True))
        form.addRow("", self.header)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.path.setText(path)

    def get_params(self) -> dict:
        return {
            "path": self.path.text().strip(),
            "format": self.fmt.currentText(),
            "mode": self.mode.currentText(),
            "header": self.header.isChecked(),
        }
