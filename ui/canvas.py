"""Canvas — center panel showing the pipeline card flow."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import theme
from models import BlockSpec
from ui.card import BlockCard


def _clear_layout(layout) -> None:
    """Remove and delete every widget/child-layout held by ``layout``."""
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        w = item.widget()
        if w is not None:
            w.hide()
            w.setParent(None)
            w.deleteLater()


class _FlowArrow(QWidget):
    """Subtle down-arrow connecting two pipeline steps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl = QLabel("\u25bc")
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl)
        self._apply_theme()
        theme.on_theme_change(self._apply_theme)

    def _apply_theme(self) -> None:
        t = theme.tokens()
        self._lbl.setStyleSheet(
            f"color: {t['arrow']}; font-size: 14px; background: transparent;"
        )


class _EmptyState(QWidget):
    """Placeholder when the pipeline has no blocks."""

    def __init__(self, on_add: callable, on_template: callable = None, parent=None):
        super().__init__(parent)
        self._on_template = on_template
        self._template_btns: list[QPushButton] = []
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        self._icon = QLabel("\U0001f3d7\ufe0f")
        self._icon.setStyleSheet("font-size: 56px; background: transparent;")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon)

        self._msg = QLabel("Start building your pipeline")
        self._msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._msg)

        self._hint = QLabel("")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hint)

        # Quick templates
        self._tmpl_label = QLabel("QUICK START TEMPLATES")
        self._tmpl_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._tmpl_label)

        tmpl_row = QHBoxLayout()
        tmpl_row.setSpacing(10)
        tmpl_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for icon_text, name in [
            ("\U0001f4ca", "CSV Analysis"),
            ("\U0001f9f9", "Data Cleaning"),
            ("\U0001f517", "Join & Enrich"),
        ]:
            btn = QPushButton(f"{icon_text}  {name}")
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if on_template:
                btn.clicked.connect(
                    lambda checked, n=name.lower().replace(" ", "_"): on_template(n)
                )
            self._template_btns.append(btn)
            tmpl_row.addWidget(btn)
        layout.addLayout(tmpl_row)

        # Shortcuts
        self._shortcuts = QLabel(
            "Ctrl+N New &nbsp;|&nbsp; Ctrl+O Open &nbsp;|&nbsp; Ctrl+S Save"
            " &nbsp;|&nbsp; Ctrl+Z Undo &nbsp;|&nbsp; Ctrl+E Edit &nbsp;|&nbsp; F1 Shortcuts"
        )
        self._shortcuts.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._shortcuts)

        self._apply_theme()
        theme.on_theme_change(self._apply_theme)

    def _apply_theme(self) -> None:
        t = theme.tokens()
        self._msg.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {t['text']}; background: transparent;"
        )
        self._hint.setText(
            f"<span style='color:{t['text_muted']};font-size:13px'>"
            f"Click <b style='color:{t['accent']}'>+ Add Block</b> or press <b>Ctrl+B</b><br>"
            f"to pick a block type and begin."
            f"</span>"
        )
        self._hint.setStyleSheet("background: transparent; padding: 4px;")
        self._tmpl_label.setStyleSheet(
            f"color: {t['text_faint']}; font-size: 11px; font-weight: 700;"
            f" letter-spacing: 1px; background: transparent; margin-top: 12px;"
        )
        btn_style = (
            f"QPushButton {{ background: {t['bg_hover']}; color: {t['text_dim']};"
            f" border: 1px solid {t['border_subtle']}; border-radius: 8px;"
            f" font-size: 12px; padding: 0 16px; }}"
            f"QPushButton:hover {{ background: {t['bg_hover_strong']};"
            f" border-color: {t['border']}; color: {t['text']}; }}"
        )
        for btn in self._template_btns:
            btn.setStyleSheet(btn_style)
        self._shortcuts.setStyleSheet(
            f"color: {t['text_faint']}; font-size: 10px; background: transparent;"
            f" margin-top: 16px;"
        )


class Canvas(QWidget):
    """Scrollable vertical card flow."""

    def __init__(self, on_add: callable, on_template: callable = None, parent=None):
        super().__init__(parent)
        self._on_add_dialog = on_add
        self._on_template = on_template
        self._block_count = 0
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        self._inner = QWidget()
        self._flow = QVBoxLayout(self._inner)
        self._flow.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._flow.setSpacing(0)
        self._flow.setContentsMargins(12, 8, 12, 12)
        self._scroll.setWidget(self._inner)
        layout.addWidget(self._scroll)

        # Compact scroll nav (always visible, top-right)
        self._nav_widget = QWidget(self)
        nav_layout = QHBoxLayout(self._nav_widget)
        nav_layout.setContentsMargins(2, 2, 2, 2)
        nav_layout.setSpacing(2)
        self._nav_btns: list[QPushButton] = []
        for text, slot in [
            ("\u25b2", self._scroll_to_top),
            ("\u25bc", self._scroll_to_bottom),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            self._nav_btns.append(btn)
            nav_layout.addWidget(btn)
        self._nav_widget.hide()

        self._apply_theme()
        theme.on_theme_change(self._apply_theme)

    def _apply_theme(self) -> None:
        t = theme.tokens()
        self._nav_widget.setStyleSheet(
            f"QWidget {{ background: {t['bg_elevated']}; border-radius: 7px;"
            f" border: 1px solid {t['border_subtle']}; }}"
        )
        nav_style = (
            f"QPushButton {{ background: transparent; color: {t['text_muted']};"
            f" border-radius: 4px; font-size: 12px; padding: 2px 8px; }}"
            f"QPushButton:hover {{ background: {t['bg_hover']}; color: {t['text']}; }}"
        )
        for btn in self._nav_btns:
            btn.setStyleSheet(nav_style)

    def _position_nav(self):
        """Pin nav widget to bottom-right of canvas."""
        w = self._nav_widget
        w.adjustSize()
        x = self.width() - w.width() - 20
        y = self.height() - w.height() - 20
        w.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_nav()

    def _scroll_to_top(self):
        self._scroll.verticalScrollBar().setValue(0)

    def _scroll_to_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def rebuild(
        self,
        blocks: list[BlockSpec],
        *,
        on_edit,
        on_delete,
        on_duplicate=None,
        on_move_up,
        on_move_down,
        on_label_changed,
        on_var_changed=None,
        on_card_clicked=None,
        on_params_changed=None,
        on_reorder=None,
    ):
        """Clear and repopulate the flow from the current pipeline state."""
        from validation import validate_pipeline

        _clear_layout(self._flow)
        total = len(blocks)
        self._block_count = total
        self._nav_widget.setVisible(total > 3)
        self._position_nav()

        if not blocks:
            self._flow.addWidget(
                _EmptyState(on_add=self._on_add_dialog, on_template=self._on_template)
            )
            return

        warnings_map = validate_pipeline(blocks)
        for i, block in enumerate(blocks):
            card = BlockCard(block, step=i + 1, total=total)
            card.edit_requested.connect(on_edit)
            card.delete_requested.connect(on_delete)
            if on_duplicate:
                card.duplicate_requested.connect(on_duplicate)
            card.move_up_requested.connect(on_move_up)
            card.move_down_requested.connect(on_move_down)
            card.label_changed.connect(on_label_changed)
            if on_var_changed:
                card.var_changed.connect(on_var_changed)
            if on_card_clicked:
                card.card_clicked.connect(on_card_clicked)
            if on_params_changed:
                card.params_changed.connect(on_params_changed)
            if on_reorder:
                card.reorder_requested.connect(on_reorder)
            msgs = warnings_map.get(block.block_id, [])
            if msgs:
                card.set_warnings(msgs)
            self._flow.addWidget(card)
            if i < total - 1:
                self._flow.addWidget(_FlowArrow())

    # ── Drag & drop reorder ──────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        block_id = event.mimeData().text()
        target = -1
        for i in range(self._flow.count()):
            w = self._flow.itemAt(i).widget()
            if w and hasattr(w, "block_id"):
                if (
                    w.geometry().top() + w.height() // 2
                    > event.position().toPoint().y()
                ):
                    target = i // 2  # cards at even indices, arrows at odd
                    break
        if target < 0:
            target = self._block_count - 1
        if block_id and target >= 0:
            # Find which card emitted this and fire reorder
            for i in range(self._flow.count()):
                w = self._flow.itemAt(i).widget()
                if w and hasattr(w, "block_id") and w.block_id == block_id:
                    w.reorder_requested.emit(block_id, target)
                    break
            event.acceptProposedAction()
