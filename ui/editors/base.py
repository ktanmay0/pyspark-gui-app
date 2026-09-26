"""Base mixin for editors — adds the "Load from Schema" combo (DRY)."""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QFormLayout

from schema import SchemaRegistry


class SchemaAwareMixin:
    """Provides _add_schema_combo() for any editor that picks columns."""

    def _add_schema_combo(
        self,
        layout: QFormLayout,
        schemas: SchemaRegistry | None,
        on_selected: callable,
    ) -> QComboBox | None:
        if not schemas or not schemas.tables:
            return None
        combo = QComboBox()
        combo.addItem("— Load columns from schema —")
        for table in schemas.tables:
            combo.addItem(f"📋 {table.table_name}", table.column_names())
        combo.currentIndexChanged.connect(
            lambda idx: self._on_schema_selected(idx, combo, on_selected)
        )
        layout.addRow("Quick-fill:", combo)
        return combo

    @staticmethod
    def _on_schema_selected(idx: int, combo: QComboBox, callback: callable):
        if idx <= 0:
            return
        cols = combo.currentData()
        if cols and callback:
            callback(cols)
