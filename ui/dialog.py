"""BlockEditorDialog — modal window that hosts the appropriate editor widget."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
)

import theme
import ui.editors  # noqa: F401  (registers editor classes onto BLOCKS)
from blocks import BLOCKS
from models import BlockSpec
from schema import SchemaRegistry


class BlockEditorDialog(QDialog):
    def __init__(
        self, block: BlockSpec, schemas: SchemaRegistry | None = None, parent=None
    ):
        super().__init__(parent)
        self.block = block
        self._schemas = schemas
        self.setWindowTitle(f"Configure: {block.label}")
        self.resize(680, 550)
        self.setMinimumSize(580, 420)

        root = QVBoxLayout(self)
        root.setSpacing(8)

        # Variable name
        var_row = QHBoxLayout()
        var_row.addWidget(QLabel("Variable name:"))
        self._var_edit = QLineEdit(block.output_var)
        self._var_edit.setPlaceholderText("e.g., orders_clean, filtered_users")
        self._var_edit.setToolTip("Name for this block's output DataFrame")
        self._var_edit.setFixedWidth(220)
        var_row.addWidget(self._var_edit)
        var_row.addStretch()
        root.addLayout(var_row)

        # Info
        t = theme.tokens()
        info = QLabel(
            f"<b>Type:</b> {block.block_type}&nbsp;&nbsp;"
            f"<b>Inputs:</b> {', '.join(block.input_vars) if block.input_vars else 'none'}"
        )
        info.setStyleSheet(
            f"color: {t['text_muted']}; font-size: 11px; padding: 4px;"
        )
        root.addWidget(info)

        # Editor
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        editor_cls = BLOCKS.get(block.block_type)
        editor_cls = editor_cls.editor if editor_cls else None
        if editor_cls:
            try:
                self.editor = editor_cls(block.params, schemas=schemas)
            except TypeError:
                self.editor = editor_cls(block.params)
            scroll.setWidget(self.editor)
        else:
            self.editor = None
            scroll.setWidget(QLabel(f"No editor for: {block.block_type}"))
        root.addWidget(scroll, stretch=1)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._focus_first()

    def _focus_first(self):
        if self.editor is None:
            return
        from PyQt6.QtWidgets import QComboBox, QLineEdit, QTextEdit

        for w in self.editor.findChildren((QLineEdit, QTextEdit, QComboBox)):
            if w.isVisible() and w.isEnabled():
                w.setFocus()
                break

    def get_block(self) -> BlockSpec:
        new_name = self._var_edit.text().strip()
        if new_name:
            self.block.output_var = new_name
        if self.editor:
            self.block.params = self.editor.get_params()
        return self.block
