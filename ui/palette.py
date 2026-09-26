"""Palette — compact block-type buttons, works as panel or slide-out drawer."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import theme
from blocks import PALETTE as BLOCK_TYPES


class Palette(QWidget):
    """Scrollable list of block-type buttons."""

    def __init__(self, on_block_clicked: callable, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(168)
        self._on_block_clicked = on_block_clicked
        self._buttons: list[QPushButton] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 6, 8)
        layout.setSpacing(4)

        self._header = QLabel("BLOCKS")
        self._header.setStyleSheet("font-size: 11px; font-weight: 700; padding: 2px 6px;")
        layout.addWidget(self._header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setSpacing(2)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for label, btype in BLOCK_TYPES:
            btn = QPushButton(label)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, bt=btype: on_block_clicked(bt))
            self._buttons.append(btn)
            inner_layout.addWidget(btn)

        inner_layout.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        self._apply_theme()
        theme.on_theme_change(self._apply_theme)

    def _apply_theme(self) -> None:
        t = theme.tokens()
        self._header.setStyleSheet(
            f"color: {t['text_muted']}; background: transparent;"
            f" font-size: 11px; font-weight: 700; letter-spacing: 1px;"
            f" padding: 2px 6px 6px 6px;"
        )
        btn_style = (
            f"QPushButton {{ text-align: left; padding: 5px 12px;"
            f" background: {t['bg_hover']}; color: {t['text_dim']};"
            f" border: 1px solid transparent; border-radius: 6px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {t['bg_hover_strong']};"
            f" border-color: {t['border_subtle']}; color: {t['text']}; }}"
        )
        for btn in self._buttons:
            btn.setStyleSheet(btn_style)
