"""Editor for string operation blocks."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from schema import SchemaRegistry
from ui.widgets import add_autocomplete

STRING_OPS = {
    "upper": [],
    "lower": [],
    "trim": [],
    "ltrim": [],
    "rtrim": [],
    "length": [],
    "reverse": [],
    "initcap": [],
    "substring": ["start", "length"],
    "split": ["delimiter"],
    "concat": ["concat_cols"],
    "concat_ws": ["separator", "concat_cols"],
    "regexp_replace": ["pattern", "replacement"],
    "lpad": ["pad_len", "pad_char"],
    "rpad": ["pad_len", "pad_char"],
    "translate": ["matching", "replace"],
}


class StringOpEditor(QWidget):
    def __init__(
        self,
        params: dict | None = None,
        schemas: SchemaRegistry | None = None,
        **kwargs,
    ):
        super().__init__()
        self._schemas = schemas
        p = params or {}
        form = QFormLayout(self)
        form.setSpacing(6)

        self.op = QComboBox()
        self.op.addItems(list(STRING_OPS))
        self.op.setCurrentText(p.get("operation", "upper"))
        self.op.currentTextChanged.connect(self._on_op_change)
        form.addRow("Operation:", self.op)

        self.output_col = QLineEdit(p.get("output_column", ""))
        self.output_col.setPlaceholderText("output column name")
        form.addRow("Output Col:", self.output_col)

        self.col = QLineEdit(p.get("col", ""))
        self.col.setPlaceholderText("input column")
        add_autocomplete(self.col, schemas)
        form.addRow("Column:", self.col)

        self.start = QSpinBox()
        self.start.setValue(p.get("start", 1))
        self.start.setMinimum(1)
        form.addRow("Start:", self.start)

        self.length = QSpinBox()
        self.length.setValue(p.get("length", 1))
        self.length.setMinimum(1)
        form.addRow("Length:", self.length)

        self.delimiter = QLineEdit(p.get("delimiter", ","))
        form.addRow("Delimiter:", self.delimiter)

        self.separator = QLineEdit(p.get("separator", ","))
        form.addRow("Separator:", self.separator)

        concat_row = QHBoxLayout()
        self.concat_cols = QLineEdit(", ".join(p.get("concat_cols", [])))
        self.concat_cols.setPlaceholderText("col1, col2, …")
        concat_row.addWidget(self.concat_cols)
        form.addRow("Concat Cols:", concat_row)

        self.pattern = QLineEdit(p.get("pattern", ""))
        form.addRow("Pattern:", self.pattern)

        self.replacement = QLineEdit(p.get("replacement", ""))
        form.addRow("Replacement:", self.replacement)

        self.pad_len = QSpinBox()
        self.pad_len.setValue(p.get("pad_len", 10))
        self.pad_len.setMinimum(1)
        form.addRow("Pad Length:", self.pad_len)

        self.pad_char = QLineEdit(p.get("pad_char", " "))
        form.addRow("Pad Char:", self.pad_char)

        self.matching = QLineEdit(p.get("matching", ""))
        form.addRow("Matching:", self.matching)

        self.replace = QLineEdit(p.get("replace", ""))
        form.addRow("Replace:", self.replace)

        self._on_op_change(self.op.currentText())

    def _on_op_change(self, op: str):
        visible_params = set(STRING_OPS.get(op, []))
        self.start.setVisible("start" in visible_params)
        self.length.setVisible("length" in visible_params)
        self.delimiter.setVisible("delimiter" in visible_params)
        self.separator.setVisible("separator" in visible_params)
        self.concat_cols.setVisible("concat_cols" in visible_params)
        self.pattern.setVisible("pattern" in visible_params)
        self.replacement.setVisible("replacement" in visible_params)
        self.pad_len.setVisible("pad_len" in visible_params)
        self.pad_char.setVisible("pad_char" in visible_params)
        self.matching.setVisible("matching" in visible_params)
        self.replace.setVisible("replace" in visible_params)

    def get_params(self) -> dict:
        return {
            "operation": self.op.currentText(),
            "output_column": self.output_col.text().strip(),
            "col": self.col.text().strip(),
            "start": self.start.value(),
            "length": self.length.value(),
            "delimiter": self.delimiter.text() or ",",
            "separator": self.separator.text() or ",",
            "concat_cols": [
                c.strip() for c in self.concat_cols.text().split(",") if c.strip()
            ],
            "pattern": self.pattern.text(),
            "replacement": self.replacement.text(),
            "pad_len": self.pad_len.value(),
            "pad_char": self.pad_char.text() or " ",
            "matching": self.matching.text(),
            "replace": self.replace.text(),
        }
