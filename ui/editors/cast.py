"""Editor for cast blocks — column → type mappings."""

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

from schema import SPARK_TYPES, SchemaRegistry
from ui.widgets import add_autocomplete


class _CastRow(QFrame):
    def __init__(
        self,
        column: str = "",
        target: str = "StringType",
        schemas: SchemaRegistry | None = None,
    ):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        self.col_edit = QLineEdit(column)
        self.col_edit.setPlaceholderText("column")
        add_autocomplete(self.col_edit, schemas)
        layout.addWidget(self.col_edit)
        layout.addWidget(QLabel("→"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(SPARK_TYPES)
        self.type_combo.setCurrentText(target)
        layout.addWidget(self.type_combo)
        rm = QPushButton("✕")
        rm.setFixedSize(24, 24)
        rm.clicked.connect(self.deleteLater)
        layout.addWidget(rm)

    def get_data(self) -> dict:
        return {
            "column": self.col_edit.text().strip(),
            "target_type": self.type_combo.currentText(),
        }


class CastEditor(QWidget):
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

        self._rows = QVBoxLayout()
        self._rows.setSpacing(2)
        layout.addLayout(self._rows)

        for c in p.get("casts", [{"column": "", "target_type": "StringType"}]):
            self._rows.addWidget(
                _CastRow(
                    c.get("column", ""),
                    c.get("target_type", "StringType"),
                    schemas=schemas,
                )
            )

        add_btn = QPushButton("+ Add Cast")
        add_btn.clicked.connect(
            lambda: self._rows.addWidget(_CastRow(schemas=self._schemas))
        )
        layout.addWidget(add_btn)

    def get_params(self) -> dict:
        casts = []
        for i in range(self._rows.count()):
            w = self._rows.itemAt(i).widget()
            if isinstance(w, _CastRow):
                d = w.get_data()
                if d["column"]:
                    casts.append(d)
        return {"casts": casts}
