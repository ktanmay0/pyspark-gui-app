"""Shared UI widgets / helpers used across editor dialogs.

Keeps Qt-dependent helpers out of the pure data layer (``schema.py``).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCompleter, QLineEdit

import theme
from schema import SchemaRegistry


def add_autocomplete(widget: QLineEdit, schemas: SchemaRegistry | None) -> None:
    """Attach schema-aware column-name autocomplete to a QLineEdit."""
    if schemas is None:
        return
    names = schemas.all_column_names()
    if not names:
        return
    comp = QCompleter(names, widget)
    comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    comp.setFilterMode(Qt.MatchFlag.MatchContains)
    # Theme the popup to match the active palette.
    popup = comp.popup()
    if popup is not None:
        t = theme.tokens()
        popup.setStyleSheet(
            f"QListView {{ background: {t['bg_surface']}; color: {t['text']};"
            f" border: 1px solid {t['border']};"
            f" selection-background-color: {t['accent']};"
            f" selection-color: {t['accent_text']}; }}"
        )
    widget.setCompleter(comp)
