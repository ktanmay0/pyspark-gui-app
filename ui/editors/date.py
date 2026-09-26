"""Editor for date/time operation blocks."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from schema import SchemaRegistry
from ui.widgets import add_autocomplete

DATE_OPS = {
    "current_date": [],
    "current_timestamp": [],
    "to_date": ["fmt"],
    "to_timestamp": ["fmt"],
    "date_add": ["days"],
    "date_sub": ["days"],
    "datediff": ["start_col", "end_col"],
    "months_between": ["start_col", "end_col"],
    "add_months": ["months"],
    "year": [],
    "month": [],
    "dayofmonth": [],
    "dayofweek": [],
    "dayofyear": [],
    "hour": [],
    "minute": [],
    "second": [],
    "last_day": [],
    "trunc": ["trunc_fmt"],
    "date_format": ["fmt"],
}


class DateOpEditor(QWidget):
    def __init__(
        self,
        params: dict | None = None,
        schemas: SchemaRegistry | None = None,
        **kwargs,
    ):
        super().__init__()
        p = params or {}
        form = QFormLayout(self)
        form.setSpacing(6)

        self.op = QComboBox()
        self.op.addItems(list(DATE_OPS))
        self.op.setCurrentText(p.get("operation", "year"))
        self.op.currentTextChanged.connect(self._on_op_change)
        form.addRow("Operation:", self.op)

        self.output_col = QLineEdit(p.get("output_column", ""))
        self.output_col.setPlaceholderText("output column name")
        form.addRow("Output Col:", self.output_col)

        self.col = QLineEdit(p.get("col", ""))
        self.col.setPlaceholderText("input column")
        add_autocomplete(self.col, schemas)
        form.addRow("Column:", self.col)

        self.fmt = QLineEdit(p.get("fmt", "yyyy-MM-dd"))
        form.addRow("Format:", self.fmt)

        self.days = QSpinBox()
        self.days.setValue(p.get("days", 1))
        form.addRow("Days:", self.days)

        self.months = QSpinBox()
        self.months.setValue(p.get("months", 1))
        form.addRow("Months:", self.months)

        self.start_col = QLineEdit(p.get("start_col", "start"))
        add_autocomplete(self.start_col, schemas)
        form.addRow("Start Col:", self.start_col)

        self.end_col = QLineEdit(p.get("end_col", "end"))
        add_autocomplete(self.end_col, schemas)
        form.addRow("End Col:", self.end_col)

        self.trunc_fmt = QComboBox()
        self.trunc_fmt.addItems(["year", "yyyy", "quarter", "month", "week", "day"])
        self.trunc_fmt.setCurrentText(p.get("trunc_fmt", "month"))
        form.addRow("Trunc To:", self.trunc_fmt)

        self._on_op_change(self.op.currentText())

    def _on_op_change(self, op: str):
        visible = set(DATE_OPS.get(op, []))
        self.fmt.setVisible("fmt" in visible)
        self.days.setVisible("days" in visible)
        self.months.setVisible("months" in visible)
        self.start_col.setVisible("start_col" in visible)
        self.end_col.setVisible("end_col" in visible)
        self.trunc_fmt.setVisible("trunc_fmt" in visible)

    def get_params(self) -> dict:
        return {
            "operation": self.op.currentText(),
            "output_column": self.output_col.text().strip(),
            "col": self.col.text().strip(),
            "fmt": self.fmt.text() or "yyyy-MM-dd",
            "days": self.days.value(),
            "months": self.months.value(),
            "start_col": self.start_col.text().strip(),
            "end_col": self.end_col.text().strip(),
            "trunc_fmt": self.trunc_fmt.currentText(),
        }
