"""Editor for window function blocks — partition, order, frame, function."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from schema import SchemaRegistry
from ui.widgets import add_autocomplete

WINDOW_FUNCTIONS = [
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "ntile",
    "lead",
    "lag",
    "sum",
    "avg",
    "min",
    "max",
    "count",
    "first",
    "last",
    "cume_dist",
]
FRAME_TYPES = ["unbounded", "rows", "range"]
FRAME_BOUNDARIES = ["unbounded_preceding", "current", "unbounded_following"]

_PARAM_VISIBILITY: dict[str, list[str]] = {
    "agg_col": ["sum", "avg", "min", "max", "count", "first", "last"],
    "lead_lag_col": ["lead", "lag"],
    "lead_lag_offset": ["lead", "lag"],
    "ntile_n": ["ntile"],
}


class _OrderRow(QFrame):
    def __init__(
        self,
        column: str = "",
        direction: str = "asc",
        schemas: SchemaRegistry | None = None,
    ):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        self.col = QLineEdit(column)
        self.col.setPlaceholderText("column")
        add_autocomplete(self.col, schemas)
        layout.addWidget(self.col)
        self.dir = QComboBox()
        self.dir.addItems(["asc", "desc"])
        self.dir.setCurrentText(direction)
        layout.addWidget(self.dir)
        rm = QPushButton("✕")
        rm.setFixedSize(24, 24)
        rm.clicked.connect(self.deleteLater)
        layout.addWidget(rm)

    def get_data(self) -> dict:
        return {"column": self.col.text().strip(), "direction": self.dir.currentText()}


class WindowEditor(QWidget):
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

        self.output_col = QLineEdit(p.get("output_column", "new_col"))
        form.addRow("Output Column:", self.output_col)

        self.func = QComboBox()
        self.func.addItems(WINDOW_FUNCTIONS)
        self.func.setCurrentText(p.get("function", "row_number"))
        self.func.currentTextChanged.connect(self._on_func_change)
        form.addRow("Function:", self.func)

        # Conditional params
        self.agg_col = QLineEdit(p.get("agg_col", ""))
        self.agg_col.setPlaceholderText("column to aggregate")
        add_autocomplete(self.agg_col, schemas)
        form.addRow("Agg Column:", self.agg_col)

        self.lead_lag_col = QLineEdit(p.get("lead_lag_col", ""))
        self.lead_lag_col.setPlaceholderText("column")
        add_autocomplete(self.lead_lag_col, schemas)
        form.addRow("Lead/Lag Col:", self.lead_lag_col)

        self.lead_lag_offset = QSpinBox()
        self.lead_lag_offset.setValue(p.get("lead_lag_offset", 1))
        form.addRow("Offset:", self.lead_lag_offset)

        self.ntile_n = QSpinBox()
        self.ntile_n.setValue(p.get("ntile_n", 4))
        self.ntile_n.setMinimum(1)
        form.addRow("Ntile N:", self.ntile_n)

        # Partition By
        part_row = QHBoxLayout()
        self.partition = QLineEdit(", ".join(p.get("partition_by", [])))
        self.partition.setPlaceholderText("col1, col2, …")
        add_autocomplete(self.partition, schemas)
        part_row.addWidget(self.partition)
        form.addRow("Partition By:", part_row)

        # Order By
        self._order_layout = QVBoxLayout()
        for o in p.get("order_by", [{"column": "", "direction": "asc"}]):
            self._order_layout.addWidget(
                _OrderRow(
                    o.get("column", ""), o.get("direction", "asc"), schemas=schemas
                )
            )
        form.addRow("Order By:", self._order_layout)

        add_order = QPushButton("+ Add Order Column")
        add_order.clicked.connect(
            lambda: self._order_layout.addWidget(_OrderRow(schemas=self._schemas))
        )
        form.addRow("", add_order)

        # Frame
        self.frame_type = QComboBox()
        self.frame_type.addItems(FRAME_TYPES)
        selected = p.get("frame_type", "unbounded")
        # Smart default
        if not p:
            selected = (
                "rows"
                if p.get("function", "row_number") in _PARAM_VISIBILITY["agg_col"]
                else "unbounded"
            )
        self.frame_type.setCurrentText(selected)
        self.frame_type.currentTextChanged.connect(self._on_frame_change)
        form.addRow("Frame Type:", self.frame_type)

        self.frame_start = QComboBox()
        self.frame_start.addItems(FRAME_BOUNDARIES)
        self.frame_start.setCurrentText(p.get("frame_start", "unbounded_preceding"))
        form.addRow("Start:", self.frame_start)

        self.frame_end = QComboBox()
        self.frame_end.addItems(FRAME_BOUNDARIES)
        self.frame_end.setCurrentText(p.get("frame_end", "current"))
        form.addRow("End:", self.frame_end)

        self._on_func_change(self.func.currentText())
        self._on_frame_change(self.frame_type.currentText())

    def _on_func_change(self, fn: str):
        self.agg_col.setVisible(fn in _PARAM_VISIBILITY["agg_col"])
        self.lead_lag_col.setVisible(fn in _PARAM_VISIBILITY["lead_lag_col"])
        self.lead_lag_offset.setVisible(fn in _PARAM_VISIBILITY["lead_lag_offset"])
        self.ntile_n.setVisible(fn in _PARAM_VISIBILITY["ntile_n"])

    def _on_frame_change(self, ft: str):
        show = ft in ("rows", "range")
        self.frame_start.setVisible(show)
        self.frame_end.setVisible(show)

    def get_params(self) -> dict:
        order_by = []
        for i in range(self._order_layout.count()):
            w = self._order_layout.itemAt(i).widget()
            if isinstance(w, _OrderRow):
                d = w.get_data()
                if d["column"]:
                    order_by.append(d)
        return {
            "output_column": self.output_col.text().strip() or "new_col",
            "function": self.func.currentText(),
            "agg_col": self.agg_col.text().strip(),
            "lead_lag_col": self.lead_lag_col.text().strip(),
            "lead_lag_offset": self.lead_lag_offset.value(),
            "ntile_n": self.ntile_n.value(),
            "partition_by": [
                c.strip() for c in self.partition.text().split(",") if c.strip()
            ],
            "order_by": order_by,
            "frame_type": self.frame_type.currentText(),
            "frame_start": self.frame_start.currentText(),
            "frame_end": self.frame_end.currentText(),
        }
