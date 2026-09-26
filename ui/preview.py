"""Preview — right panel showing live PySpark code."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import theme
from ui.highlighter import PythonHighlighter


class Preview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        hdr = QHBoxLayout()
        self._title = QLabel("\U0001f4dd  PySpark Code")
        hdr.addWidget(self._title)
        hdr.addStretch()

        self._toggle_btn = QPushButton("Hide \u25b8")
        self._toggle_btn.setFixedSize(78, 26)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle)
        hdr.addWidget(self._toggle_btn)
        layout.addLayout(hdr)

        self._editor = QTextEdit()
        self._editor.setReadOnly(True)
        self._editor.setFont(QFont("Consolas", 12))
        self._highlighter = PythonHighlighter(self._editor.document())
        layout.addWidget(self._editor)

        self._last_code = ""  # cache to skip no-op updates
        self._apply_theme()
        theme.on_theme_change(self._apply_theme)

    def _apply_theme(self) -> None:
        t = theme.tokens()
        self._title.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {t['text']};"
            f" background: transparent; padding: 4px 0;"
        )
        self._toggle_btn.setStyleSheet(
            f"QPushButton {{ background: {t['bg_surface']}; color: {t['text_dim']};"
            f" border: 1px solid {t['border']}; border-radius: 5px; font-size: 11px; }}"
            f" QPushButton:hover {{ color: {t['text']}; border-color: {t['border_strong']}; }}"
        )
        self._editor.setStyleSheet(
            f"QTextEdit {{ background-color: {t['bg_elevated']}; color: {t['text']};"
            f" border: 1px solid {t['border']}; border-radius: 8px; padding: 10px; }}"
        )
        self._highlighter._apply_theme()

    def set_code(self, code: str):
        # Skip the expensive setPlainText + full re-highlight if nothing
        # changed (e.g. canvas rebuild after a label-only edit).
        if code != self._last_code:
            self._last_code = code
            self._editor.setPlainText(code)

    def _toggle(self):
        visible = self._editor.isVisible()
        self._editor.setVisible(not visible)
        self._toggle_btn.setText("Show \u25c2" if visible else "Hide \u25b8")
