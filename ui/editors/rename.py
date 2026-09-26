"""Editor for rename blocks — dynamic old→new mapping rows."""

from __future__ import annotations

from PyQt6.QtWidgets import (
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


class _RenameRow(QFrame):
    def __init__(
        self, old: str = "", new: str = "", schemas: SchemaRegistry | None = None
    ):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        self.old_edit = QLineEdit(old)
        self.old_edit.setPlaceholderText("current name")
        add_autocomplete(self.old_edit, schemas)
        layout.addWidget(self.old_edit)
        layout.addWidget(QLabel("→"))
        self.new_edit = QLineEdit(new)
        self.new_edit.setPlaceholderText("new name")
        layout.addWidget(self.new_edit)
        rm = QPushButton("✕")
        rm.setFixedSize(24, 24)
        rm.clicked.connect(self.deleteLater)
        layout.addWidget(rm)

    def get_data(self) -> dict:
        return {
            "old": self.old_edit.text().strip(),
            "new": self.new_edit.text().strip(),
        }


class RenameEditor(QWidget):
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

        for m in p.get("mappings", [{"old": "", "new": ""}]):
            self._rows.addWidget(
                _RenameRow(m.get("old", ""), m.get("new", ""), schemas=schemas)
            )

        add_btn = QPushButton("+ Add Mapping")
        add_btn.clicked.connect(
            lambda: self._rows.addWidget(_RenameRow(schemas=self._schemas))
        )
        layout.addWidget(add_btn)

    def get_params(self) -> dict:
        mappings = []
        for i in range(self._rows.count()):
            w = self._rows.itemAt(i).widget()
            if isinstance(w, _RenameRow):
                d = w.get_data()
                if d["old"] and d["new"]:
                    mappings.append(d)
        return {"mappings": mappings}
