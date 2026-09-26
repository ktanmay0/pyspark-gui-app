"""Contextual help panel — reads block descriptions from blocks.py."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

import theme
from blocks import BLOCKS

_PLACEHOLDER = (
    "<b style='font-size:14px'>\U0001f4a1 Help</b><br><br>"
    "<span style='font-size:12px'>"
    "Click a block to see what it does.<br><br>"
    "Each block is one step in your data pipeline — just like a recipe.</span>"
)


class HelpPanel(QWidget):
    """Collapsible panel showing contextual help for the selected block type."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(248)
        self.setMaximumWidth(340)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self._content = QLabel(_PLACEHOLDER)
        self._content.setWordWrap(True)
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._content)
        layout.addStretch()

        self._apply_theme()
        theme.on_theme_change(self._apply_theme)

    def _apply_theme(self) -> None:
        t = theme.tokens()
        self.setStyleSheet(f"HelpPanel {{ background: {t['bg_elevated']}; border-left: 1px solid {t['border']}; }}")
        self._refresh_colors()

    def _refresh_colors(self) -> None:
        t = theme.tokens()
        self._content.setStyleSheet(f"color: {t['text']}; background: transparent;")

    def show_for_block(self, block_type: str | None):
        t = theme.tokens()
        bt = BLOCKS.get(block_type) if block_type else None
        if bt is None or not bt.help_title:
            self._content.setText(_PLACEHOLDER)
            self._refresh_colors()
            return
        self._content.setText(
            f"<b style='font-size:15px'>{bt.help_title}</b><br><br>"
            f"<b>What it does:</b><br>"
            f"<span style='font-size:12px'>{bt.help_what}</span><br><br>"
            f"<b>Example:</b><br>"
            f"<span style='color:{t['accent']}; font-size:12px'>{bt.help_example}</span><br><br>"
            f"<b>\U0001f4a1 Tip:</b><br>"
            f"<span style='font-size:12px'>{bt.help_tip}</span>"
        )
        self._refresh_colors()
