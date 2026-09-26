"""Editor for filter blocks — dynamic condition rows with column autocomplete."""

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

from helpers import LOGICAL_OPS, OPERATORS, VALUE_TYPES
from schema import SchemaRegistry
from ui.widgets import add_autocomplete


class _ConditionRow(QFrame):
    def __init__(
        self,
        is_first: bool,
        data: dict | None = None,
        schemas: SchemaRegistry | None = None,
    ):
        super().__init__()
        d = data or {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(4)

        self.logical_combo = QComboBox()
        self.logical_combo.addItems(LOGICAL_OPS)
        self.logical_combo.setFixedWidth(65)
        if is_first:
            self.logical_combo.hide()
        else:
            self.logical_combo.setCurrentText(d.get("logical_op", "AND"))
        layout.addWidget(self.logical_combo)
        layout.addWidget(QLabel("where"))
        layout.addSpacing(2)

        self.col_edit = QLineEdit(d.get("column", ""))
        self.col_edit.setPlaceholderText("e.g., age, status, amount")
        self.col_edit.setFixedWidth(130)
        add_autocomplete(self.col_edit, schemas)
        layout.addWidget(self.col_edit)

        self.op_combo = QComboBox()
        self.op_combo.addItems(OPERATORS)
        self.op_combo.setCurrentText(d.get("operator", "=="))
        self.op_combo.setFixedWidth(105)
        self.op_combo.currentTextChanged.connect(self._on_op_change)
        layout.addWidget(self.op_combo)

        self.val_edit = QLineEdit(d.get("value", ""))
        self.val_edit.setPlaceholderText('e.g., 18, "active", 100')
        self.val_edit.setFixedWidth(130)
        layout.addWidget(self.val_edit)

        self.val_type = QComboBox()
        self.val_type.addItems(VALUE_TYPES)
        self.val_type.setCurrentText(d.get("value_type", "literal"))
        self.val_type.setFixedWidth(75)
        layout.addWidget(self.val_type)

        rm = QPushButton("✕")
        rm.setFixedSize(24, 24)
        rm.setToolTip("Remove")
        rm.clicked.connect(self.deleteLater)
        layout.addWidget(rm)
        layout.addStretch()
        self._on_op_change(self.op_combo.currentText())

    def _on_op_change(self, op: str):
        no_val = op in ("isNull", "isNotNull")
        self.val_edit.setVisible(not no_val)
        self.val_type.setVisible(not no_val)

    def get_data(self) -> dict:
        return {
            "column": self.col_edit.text().strip(),
            "operator": self.op_combo.currentText(),
            "value": self.val_edit.text().strip(),
            "value_type": self.val_type.currentText(),
            "logical_op": self.logical_combo.currentText()
            if self.logical_combo.isVisible()
            else None,
        }


class FilterEditor(QWidget):
    def __init__(
        self,
        params: dict | None = None,
        schemas: SchemaRegistry | None = None,
        **kwargs,
    ):
        super().__init__()
        self._schemas = schemas
        p = params or {}
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Schema quick-fill
        if schemas and schemas.tables:

            top_row = QHBoxLayout()
            top_row.addWidget(QLabel("Quick-fill from:"))
            self._schema_combo = QComboBox()
            self._schema_combo.addItem("— choose schema —")
            for t in schemas.tables:
                self._schema_combo.addItem(f"📋 {t.table_name}", t.column_names())
            self._schema_combo.currentIndexChanged.connect(self._on_schema)
            top_row.addWidget(self._schema_combo, stretch=1)
            layout.addLayout(top_row)
        else:
            self._schema_combo = None

        layout.addWidget(
            QLabel("Define filter conditions. Extra rows chain with AND/OR.")
        )
        self._rows = QVBoxLayout()
        self._rows.setSpacing(2)
        layout.addLayout(self._rows)

        conditions = p.get("conditions", []) or [{}]
        for i, cond in enumerate(conditions):
            self._rows.addWidget(
                _ConditionRow(is_first=(i == 0), data=cond, schemas=schemas)
            )

        add_btn = QPushButton("+ Add Condition")
        add_btn.clicked.connect(
            lambda: self._rows.addWidget(
                _ConditionRow(is_first=(self._rows.count() == 0), schemas=self._schemas)
            )
        )
        layout.addWidget(add_btn)

    def _on_schema(self, idx: int):
        if idx <= 0 or self._schema_combo is None:
            return
        cols = self._schema_combo.currentData()
        if cols and self._rows.count() > 0:
            w = self._rows.itemAt(0).widget()
            if isinstance(w, _ConditionRow) and cols:
                w.col_edit.setText(cols[0])

    def get_params(self) -> dict:
        conditions = []
        for i in range(self._rows.count()):
            w = self._rows.itemAt(i).widget()
            if isinstance(w, _ConditionRow):
                d = w.get_data()
                if d.get("column"):
                    conditions.append(d)
        return {"conditions": conditions}
