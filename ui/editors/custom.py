"""Editor for custom code blocks — free-form PySpark snippet."""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget


class CustomEditor(QWidget):
    def __init__(self, params: dict | None = None, **kwargs):
        super().__init__()
        p = params or {}
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        layout.addWidget(
            QLabel(
                "Paste any PySpark code below. It will be inserted verbatim into the generated script."
            )
        )
        self._code = QTextEdit()
        self._code.setPlaceholderText("# Your custom PySpark code here…")
        self._code.setPlainText(p.get("code", ""))
        layout.addWidget(self._code)

    def get_params(self) -> dict:
        return {"code": self._code.toPlainText()}
