"""Editor for when/otherwise blocks — branch-based conditional logic."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from helpers import LOGICAL_OPS, OPERATORS, RESULT_TYPES, VALUE_TYPES
from schema import SchemaRegistry
from ui.widgets import add_autocomplete


class _BranchConditionRow(QFrame):
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

        self.logical = QComboBox()
        self.logical.addItems(LOGICAL_OPS)
        self.logical.setFixedWidth(65)
        if is_first:
            self.logical.hide()
        else:
            self.logical.setCurrentText(d.get("logical_op", "AND"))
        layout.addWidget(self.logical)
        layout.addWidget(QLabel("when"))
        layout.addSpacing(2)

        self.col = QLineEdit(d.get("column", ""))
        self.col.setPlaceholderText("column")
        self.col.setFixedWidth(110)
        add_autocomplete(self.col, schemas)
        layout.addWidget(self.col)

        self.op = QComboBox()
        self.op.addItems(OPERATORS)
        self.op.setCurrentText(d.get("operator", "=="))
        self.op.setFixedWidth(95)
        self.op.currentTextChanged.connect(
            lambda o: self._toggle_val(o in ("isNull", "isNotNull"))
        )
        layout.addWidget(self.op)

        self.val = QLineEdit(d.get("value", ""))
        self.val.setPlaceholderText("value")
        self.val.setFixedWidth(100)
        layout.addWidget(self.val)

        self.val_type = QComboBox()
        self.val_type.addItems(VALUE_TYPES)
        self.val_type.setCurrentText(d.get("value_type", "literal"))
        self.val_type.setFixedWidth(70)
        layout.addWidget(self.val_type)

        rm = QPushButton("✕")
        rm.setFixedSize(24, 24)
        rm.clicked.connect(self.deleteLater)
        layout.addWidget(rm)
        layout.addStretch()

        self._toggle_val(d.get("operator", "==") in ("isNull", "isNotNull"))

    def _toggle_val(self, hide: bool):
        self.val.setVisible(not hide)
        self.val_type.setVisible(not hide)

    def get_data(self) -> dict:
        return {
            "column": self.col.text().strip(),
            "operator": self.op.currentText(),
            "value": self.val.text().strip(),
            "value_type": self.val_type.currentText(),
            "logical_op": self.logical.currentText()
            if self.logical.isVisible()
            else None,
        }


class _BranchGroup(QGroupBox):
    def __init__(
        self,
        title: str,
        data: dict | None = None,
        schemas: SchemaRegistry | None = None,
    ):
        super().__init__(title)
        self._schemas = schemas
        d = data or {}
        layout = QVBoxLayout(self)

        conds_layout = QVBoxLayout()
        conds = d.get("conditions", []) or [{}]
        for i, c in enumerate(conds):
            conds_layout.addWidget(
                _BranchConditionRow(is_first=(i == 0), data=c, schemas=schemas)
            )
        layout.addLayout(conds_layout)

        add_cond = QPushButton("+ Add Condition")
        add_cond.clicked.connect(
            lambda: conds_layout.addWidget(
                _BranchConditionRow(
                    is_first=(conds_layout.count() == 0), schemas=self._schemas
                )
            )
        )
        layout.addWidget(add_cond)

        result_row = QHBoxLayout()
        result_row.addWidget(QLabel("then:"))
        self.result_val = QLineEdit(d.get("result_value", ""))
        self.result_val.setPlaceholderText("value")
        result_row.addWidget(self.result_val)
        self.result_type = QComboBox()
        self.result_type.addItems(RESULT_TYPES)
        self.result_type.setCurrentText(d.get("result_type", "literal"))
        result_row.addWidget(self.result_type)
        layout.addLayout(result_row)

        self._conds_layout = conds_layout

    def get_data(self) -> dict:
        conds = []
        for i in range(self._conds_layout.count()):
            w = self._conds_layout.itemAt(i).widget()
            if isinstance(w, _BranchConditionRow):
                d = w.get_data()
                if d.get("column"):
                    conds.append(d)
        return {
            "conditions": conds,
            "result_value": self.result_val.text().strip(),
            "result_type": self.result_type.currentText(),
        }


class WhenOtherwiseEditor(QWidget):
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

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output column:"))
        self.output_col = QLineEdit(p.get("output_column", "new_col"))
        self.output_col.setPlaceholderText("new_col")
        out_row.addWidget(self.output_col)
        layout.addLayout(out_row)

        self._branches_layout = QVBoxLayout()
        layout.addLayout(self._branches_layout)

        for b in p.get("branches", [{}]):
            self._branches_layout.addWidget(
                _BranchGroup(
                    f"Branch {self._branches_layout.count() + 1}",
                    data=b,
                    schemas=schemas,
                )
            )

        add_br = QPushButton("+ Add Branch")
        add_br.clicked.connect(
            lambda: self._branches_layout.addWidget(
                _BranchGroup(
                    f"Branch {self._branches_layout.count() + 1}", schemas=self._schemas
                )
            )
        )
        layout.addWidget(add_br)

        # Otherwise
        else_row = QHBoxLayout()
        else_row.addWidget(QLabel("Otherwise:"))
        self.else_val = QLineEdit(p.get("otherwise_value", ""))
        self.else_val.setPlaceholderText("default value")
        else_row.addWidget(self.else_val)
        self.else_type = QComboBox()
        self.else_type.addItems(["null", "literal", "column"])
        self.else_type.setCurrentText(p.get("otherwise_type", "null"))
        else_row.addWidget(self.else_type)
        layout.addLayout(else_row)

    def get_params(self) -> dict:
        branches = []
        for i in range(self._branches_layout.count()):
            w = self._branches_layout.itemAt(i).widget()
            if isinstance(w, _BranchGroup):
                branches.append(w.get_data())
        return {
            "output_column": self.output_col.text().strip() or "new_col",
            "branches": branches,
            "otherwise_value": self.else_val.text().strip(),
            "otherwise_type": self.else_type.currentText(),
        }
