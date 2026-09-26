"""F1 cheatsheet — keyboard shortcuts in a friendly dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

import theme

_SHORTCUTS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "📁 Files",
        [
            ("Ctrl+N", "New pipeline"),
            ("Ctrl+O", "Open pipeline"),
            ("Ctrl+S", "Save pipeline"),
            ("Ctrl+Shift+S", "Export .py script"),
        ],
    ),
    (
        "✏️ Editing",
        [
            ("Ctrl+Z", "Undo last change"),
            ("Ctrl+Y", "Redo"),
            ("Ctrl+E", "Edit last block"),
            ("Delete", "Delete last block"),
            ("Double-click card", "Open block configuration"),
            ("Double-click label", "Rename block inline"),
        ],
    ),
    (
        "📋 Code",
        [
            ("Ctrl+Shift+C", "Copy generated code"),
            ("Ctrl+I", "Explain pipeline in plain English"),
        ],
    ),
    (
        "🎨 Appearance",
        [
            ("🌓 Toolbar button", "Toggle dark / light theme"),
            ("Hide ▸ / Show ◂", "Toggle code preview panel"),
        ],
    ),
    (
        "❓ Help",
        [
            ("F1", "Show this cheatsheet"),
            ("Click any block", "See help panel explain what it does"),
        ],
    ),
]


class CheatsheetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u2328\ufe0f Keyboard Shortcuts — Cheatsheet")
        self.resize(540, 480)
        self.setMinimumSize(440, 360)

        t = theme.tokens()
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        header = QLabel("\u2328\ufe0f  Keyboard Shortcuts")
        header.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {t['text']}; padding: 4px 0;"
        )
        layout.addWidget(header)

        for section, items in _SHORTCUTS:
            sec_lbl = QLabel(section)
            sec_lbl.setStyleSheet(
                f"font-size: 12px; font-weight: 700; color: {t['accent']};"
                f" padding: 6px 0 2px 0;"
            )
            layout.addWidget(sec_lbl)

            table = QTableWidget(len(items), 2)
            table.horizontalHeader().hide()
            table.verticalHeader().hide()
            table.setColumnWidth(0, 200)
            table.horizontalHeader().setStretchLastSection(True)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
            for i, (key, desc) in enumerate(items):
                key_item = QTableWidgetItem(key)
                key_item.setFlags(Qt.ItemFlag.NoItemFlags)
                desc_item = QTableWidgetItem(desc)
                desc_item.setFlags(Qt.ItemFlag.NoItemFlags)
                table.setItem(i, 0, key_item)
                table.setItem(i, 1, desc_item)
            table.setFixedHeight(table.rowHeight(0) * len(items) + 8)
            layout.addWidget(table)

        layout.addSpacing(8)
        tip = QLabel(
            "\U0001f4a1 Most actions also have tooltips when you hover over buttons."
        )
        tip.setWordWrap(True)
        tip.setStyleSheet(f"color: {t['text_muted']}; font-size: 11px;")
        layout.addWidget(tip)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
