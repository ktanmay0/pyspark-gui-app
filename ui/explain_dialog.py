"""Explain Pipeline dialog — plain-English walkthrough for freshers.

Shows what each block does in simple terms, the data flow between blocks,
and a pipeline composition summary.  Accessible via the More menu or Ctrl+I.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import theme
from explain import data_flow, explain_pipeline, pipeline_summary
from models import PipelineState


class ExplainDialog(QDialog):
    def __init__(self, state: PipelineState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setWindowTitle("Explain Pipeline")
        self.resize(620, 560)
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        self._header = QLabel()
        layout.addWidget(self._header)

        # Data flow
        self._flow_lbl = QLabel()
        self._flow_lbl.setWordWrap(True)
        self._flow_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self._flow_lbl)

        # Pipeline health hints
        self._hints = QLabel()
        self._hints.setWordWrap(True)
        layout.addWidget(self._hints)

        # Scrollable step list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        self._steps_layout = QVBoxLayout(inner)
        self._steps_layout.setSpacing(8)
        self._steps_layout.setContentsMargins(0, 0, 0, 0)
        self._steps_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate()
        self._apply_theme()
        theme.on_theme_change(self._apply_theme)

    def _populate(self):
        summary = pipeline_summary(self._state)
        n = summary["total_blocks"]

        # Header with summary counts
        cat_parts = [f"{v} {k.lower()}" for k, v in summary["categories"].items()]
        cat_text = ", ".join(cat_parts) if cat_parts else "no blocks"
        self._header.setText(
            f"<b style='font-size:16px'>{summary['app_name']}</b>"
            f"<br><span style='font-size:12px'>{n} {'block' if n == 1 else 'blocks'}: {cat_text}</span>"
        )

        # Data flow diagram
        flow = data_flow(self._state)
        self._flow_lbl.setText(
            f"<b style='font-size:12px'>Data flow:</b><br>"
            f"<code style='font-size:12px; white-space: pre-wrap'>{flow}</code>"
        )

        # Health hints (gentle guidance for freshers)
        hints = []
        if n == 0:
            hints.append("Your pipeline is empty. Add a 'Read Data' block to get started.")
        if n > 0 and not summary["has_read"]:
            hints.append("No 'Read Data' block — your pipeline has no data source.")
        if n > 0 and not summary["has_write"]:
            hints.append("No 'Write' block — your results won't be saved to disk.")
        if summary["categories"].get("Read", 0) > 1:
            hints.append("Multiple read blocks detected — consider a Join to combine them.")
        if hints:
            self._hints.setText(
                "<b style='font-size:12px'>Tips:</b><br>"
                + "<br>".join(f"\u2022 {h}" for h in hints)
            )
        else:
            self._hints.setText("")

        # Step-by-step explanations
        steps = explain_pipeline(self._state)
        for step in steps:
            self._steps_layout.addWidget(self._build_step(step))

    def _build_step(self, step: dict) -> QLabel:
        lbl = QLabel()
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setText(
            f"<b style='font-size:13px'>Step {step['step']}: {step['label']}</b>"
            f" <span style='font-size:11px'>({step['category']})</span><br>"
            f"<span style='font-size:12px'>{step['description']}</span>"
        )
        return lbl

    def _apply_theme(self) -> None:
        t = theme.tokens()
        self.setStyleSheet(f"QDialog {{ background: {t['bg']}; }}")
        self._header.setStyleSheet(
            f"color: {t['text']}; background: transparent; padding-bottom: 4px;"
        )
        self._flow_lbl.setStyleSheet(
            f"color: {t['text']}; background: {t['bg_base']};"
            f" border: 1px solid {t['border']}; border-radius: 6px; padding: 10px;"
        )
        hint_color = t["warning"] if self._hints.text() else t["text"]
        self._hints.setStyleSheet(
            f"color: {hint_color}; background: {t['bg_base']};"
            f" border: 1px solid {t['border']}; border-radius: 6px; padding: 10px;"
        )
        step_style = (
            f"color: {t['text']}; background: {t['bg_base']};"
            f" border: 1px solid {t['border']}; border-radius: 6px; padding: 10px;"
        )
        for i in range(self._steps_layout.count()):
            w = self._steps_layout.itemAt(i).widget()
            if w is not None:
                w.setStyleSheet(step_style)
