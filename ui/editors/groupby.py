"""Editor for groupby_agg blocks — with column autocomplete and Load-from-Schema."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from schema import SchemaRegistry
from ui.editors.base import SchemaAwareMixin
from ui.widgets import add_autocomplete

AGG_FUNCTIONS = [
    "sum",
    "avg",
    "mean",
    "count",
    "countDistinct",
    "min",
    "max",
    "first",
    "last",
    "stddev",
    "variance",
    "collect_list",
    "collect_set",
]


class _AggRow(QFrame):
    def __init__(
        self,
        column: str = "",
        func: str = "sum",
        alias: str = "",
        schemas: SchemaRegistry | None = None,
    ):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        self.func_combo = QComboBox()
        self.func_combo.addItems(AGG_FUNCTIONS)
        self.func_combo.setCurrentText(func)
        self.func_combo.setFixedWidth(120)
        layout.addWidget(self.func_combo)
        self.col_edit = QLineEdit(column)
        self.col_edit.setPlaceholderText("e.g., amount, salary (* for count)")
        add_autocomplete(self.col_edit, schemas)
        layout.addWidget(self.col_edit)
        self.alias_edit = QLineEdit(alias)
        self.alias_edit.setPlaceholderText("e.g., total_sales, avg_price")
        self.alias_edit.setFixedWidth(120)
        layout.addWidget(self.alias_edit)
        rm = QPushButton("✕")
        rm.setFixedSize(24, 24)
        rm.clicked.connect(self.deleteLater)
        layout.addWidget(rm)

    def get_data(self) -> dict:
        return {
            "column": self.col_edit.text().strip(),
            "function": self.func_combo.currentText(),
            "alias": self.alias_edit.text().strip(),
        }


class GroupByEditor(SchemaAwareMixin, QWidget):
    def __init__(
        self,
        params: dict | None = None,
        schemas: SchemaRegistry | None = None,
        **kwargs,
    ):
        super().__init__()
        p = params or {}
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        self._add_schema_combo_layout(layout, schemas)

        group_row = QHBoxLayout()
        group_row.addWidget(QLabel("Group By:"))
        self.group_cols = QLineEdit(", ".join(p.get("group_by_cols", [])))
        self.group_cols.setPlaceholderText("e.g., department, year, region")
        add_autocomplete(self.group_cols, schemas)
        group_row.addWidget(self.group_cols)
        layout.addLayout(group_row)

        self._agg_layout = QVBoxLayout()
        self._agg_layout.setSpacing(2)
        layout.addLayout(self._agg_layout)

        for a in p.get("aggregations", [{}]):
            self._agg_layout.addWidget(
                _AggRow(
                    a.get("column", ""),
                    a.get("function", "sum"),
                    a.get("alias", ""),
                    schemas=schemas,
                )
            )

        add_agg = QPushButton("+ Add Aggregation")
        add_agg.clicked.connect(
            lambda: self._agg_layout.addWidget(_AggRow(schemas=schemas))
        )
        layout.addWidget(add_agg)

    def _add_schema_combo_layout(self, layout: QVBoxLayout, schemas):
        """Variant that adds to a QVBoxLayout (not QFormLayout)."""
        if not schemas or not schemas.tables:
            return
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Quick-fill from:"))
        combo = QComboBox()
        combo.addItem("— choose schema —")
        for t in schemas.tables:
            combo.addItem(f"📋 {t.table_name}", t.column_names())
        combo.currentIndexChanged.connect(lambda idx: self._on_schema(idx, combo))
        top_row.addWidget(combo, stretch=1)
        layout.addLayout(top_row)

    def _on_schema(self, idx: int, combo: QComboBox):
        if idx <= 0:
            return
        cols = combo.currentData()
        if cols:
            self.group_cols.setText(", ".join(cols))

    def get_params(self) -> dict:
        group_cols = [c.strip() for c in self.group_cols.text().split(",") if c.strip()]
        aggs = []
        for i in range(self._agg_layout.count()):
            w = self._agg_layout.itemAt(i).widget()
            if isinstance(w, _AggRow):
                d = w.get_data()
                if d["column"]:
                    aggs.append(d)
        return {"group_by_cols": group_cols, "aggregations": aggs}
