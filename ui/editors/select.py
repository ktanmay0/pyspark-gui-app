"""Editor for select blocks — with schema-aware autocomplete."""

from __future__ import annotations

from PyQt6.QtWidgets import QFormLayout, QLabel, QTextEdit, QWidget

import theme
from schema import SchemaRegistry
from ui.editors.base import SchemaAwareMixin


class SelectEditor(SchemaAwareMixin, QWidget):
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

        self._add_schema_combo(
            form, schemas, lambda cols: self._text.setPlainText("\n".join(cols))
        )

        if schemas:
            cols = schemas.all_column_names()
            if cols:
                hint = (
                    f"Known columns: {', '.join(cols[:15])}"
                    f"{' …' if len(cols) > 15 else ''}"
                )
                lbl = QLabel(hint)
                t = theme.tokens()
                lbl.setStyleSheet(
                    f"color: {t['accent']}; font-size: 11px; font-style: italic;"
                )
                form.addRow(lbl)

        self._text = QTextEdit()
        self._text.setPlaceholderText(
            "one column name per line\ne.g.\ncustomer_id\norder_date\namount"
        )
        self._text.setMaximumHeight(130)
        self._text.setPlainText("\n".join(p.get("columns", [])))
        form.addRow("Columns:", self._text)

    def get_params(self) -> dict:
        return {
            "columns": [
                c.strip() for c in self._text.toPlainText().splitlines() if c.strip()
            ]
        }
