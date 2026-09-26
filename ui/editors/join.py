"""Editor for join blocks — with column autocomplete."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from schema import SchemaRegistry
from ui.widgets import add_autocomplete

JOIN_TYPES = ["inner", "left", "right", "outer", "left_semi", "left_anti", "cross"]


class _KeyRow(QFrame):
    def __init__(
        self, left: str = "", right: str = "", schemas: SchemaRegistry | None = None
    ):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        self.left_edit = QLineEdit(left)
        self.left_edit.setPlaceholderText("e.g., orders.customer_id")
        add_autocomplete(self.left_edit, schemas)
        layout.addWidget(self.left_edit)
        layout.addWidget(QLabel("="))
        self.right_edit = QLineEdit(right)
        self.right_edit.setPlaceholderText("e.g., customers.id")
        add_autocomplete(self.right_edit, schemas)
        layout.addWidget(self.right_edit)
        rm = QPushButton("✕")
        rm.setFixedSize(24, 24)
        rm.clicked.connect(self.deleteLater)
        layout.addWidget(rm)

    def get_data(self) -> dict:
        return {
            "left": self.left_edit.text().strip(),
            "right": self.right_edit.text().strip(),
        }


class JoinEditor(QWidget):
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

        form = QFormLayout()
        self.join_type = QComboBox()
        self.join_type.addItems(JOIN_TYPES)
        self.join_type.setCurrentText(p.get("join_type", "inner"))
        form.addRow("Join Type:", self.join_type)
        self.broadcast = QCheckBox("Broadcast right table")
        self.broadcast.setChecked(p.get("broadcast_right", False))
        form.addRow("", self.broadcast)
        layout.addLayout(form)

        self._keys_layout = QVBoxLayout()
        self._keys_layout.setSpacing(2)
        layout.addLayout(self._keys_layout)

        for k in p.get("join_keys", [{"left": "", "right": ""}]):
            self._keys_layout.addWidget(
                _KeyRow(k.get("left", ""), k.get("right", ""), schemas=schemas)
            )

        add_key = QPushButton("+ Add Key")
        add_key.clicked.connect(
            lambda: self._keys_layout.addWidget(_KeyRow(schemas=self._schemas))
        )
        layout.addWidget(add_key)

    def get_params(self) -> dict:
        keys = []
        for i in range(self._keys_layout.count()):
            w = self._keys_layout.itemAt(i).widget()
            if isinstance(w, _KeyRow):
                d = w.get_data()
                if d["left"] and d["right"]:
                    keys.append(d)
        return {
            "join_type": self.join_type.currentText(),
            "join_keys": keys,
            "broadcast_right": self.broadcast.isChecked(),
        }
