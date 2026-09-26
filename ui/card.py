"""BlockCard — a single pipeline-step card displayed on the canvas.

Cards show a SQL-style sentence with editable fields right on the card.
Double-click the title to rename.  Click the gear button for full dialog.
All sentence rendering is driven by blocks.py — zero hardcoded block logic.
"""

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import theme
from blocks import (
    BLOCKS,
    FieldSpec,
    count_list,
    get_field_value,
    set_field_value,
)
from models import BlockSpec

_EMPTY = "\u2014"


# ── Sentence widget styling (theme-driven) ────────────────────


def _sentence_style() -> str:
    t = theme.tokens()
    return (
        f"QLineEdit {{ background: {t['card_overlay']}; color: {t['card_text']};"
        f" border: 1px solid {t['card_border']}; border-radius: 4px;"
        f" padding: 3px 7px; font-size: 12px;"
        f" selection-background-color: {t['accent']};"
        f" selection-color: {t['accent_text']}; }}"
        f"QLineEdit:focus {{ border: 1px solid {t['card_overlay_focus']}; }}"
        f"QComboBox {{ background: {t['card_overlay']}; color: {t['card_text']};"
        f" border: 1px solid {t['card_border']}; border-radius: 4px;"
        f" padding: 2px 6px; font-size: 12px; }}"
        f"QComboBox:hover, QComboBox:focus {{ border: 1px solid {t['card_overlay_focus']}; }}"
        f"QComboBox QAbstractItemView {{ background: {t['bg_surface']}; color: {t['text']};"
        f" selection-background-color: {t['accent']};"
        f" selection-color: {t['accent_text']}; }}"
        f"QCheckBox {{ color: {t['card_text']}; font-size: 12px; spacing: 6px; }}"
        f"QCheckBox::indicator {{ width: 15px; height: 15px; border-radius: 3px; }}"
        f"QTextEdit {{ background: {t['card_overlay']}; color: {t['card_text']};"
        f" border: 1px solid {t['card_border']}; border-radius: 4px;"
        f" padding: 3px 7px; font-size: 12px; }}"
        f"QTextEdit:focus {{ border: 1px solid {t['card_overlay_focus']}; }}"
    )


def _label_style() -> str:
    t = theme.tokens()
    return f"background: transparent; color: {t['card_label']}; font-size: 13px;"


# ── Tiny widget factories ──────────────────────────────────────


def _lbl(text: str) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(_label_style())
    return l


def _inp_lbl(text: str) -> QLabel:
    t = theme.tokens()
    l = QLabel(text)
    l.setStyleSheet(
        f"background: transparent; color: {t['card_input_ref']};"
        f" font-size: 12px; font-weight: bold;"
    )
    return l


def _le(oid: str, val: str = "", ph: str = "", fw: int = 0) -> QLineEdit:
    w = QLineEdit(val)
    w.setObjectName(oid)
    w.setPlaceholderText(ph)
    if fw:
        w.setFixedWidth(fw)
    return w


def _cb(oid: str, items: list[str], cur: str = "", fw: int = 0) -> QComboBox:
    w = QComboBox()
    w.setObjectName(oid)
    w.addItems(items)
    if cur:
        w.setCurrentText(cur)
    if fw:
        w.setFixedWidth(fw)
    return w


def _chk(oid: str, text: str, checked: bool = False) -> QCheckBox:
    w = QCheckBox(text)
    w.setObjectName(oid)
    w.setChecked(checked)
    return w


def _te(oid: str, val: str = "", ph: str = "", mh: int = 60) -> QTextEdit:
    w = QTextEdit()
    w.setObjectName(oid)
    w.setPlaceholderText(ph)
    w.setPlainText(val)
    w.setMaximumHeight(mh)
    return w


# ═══════════════════════════════════════════════════════════════
#  Generic sentence renderer (data-driven from blocks.py)
# ═══════════════════════════════════════════════════════════════


def _build_sentence(block: BlockSpec) -> QWidget:
    """Build a sentence widget from the block's FieldSpec list."""
    bt = BLOCKS.get(block.block_type)
    if bt is None:
        return QLabel(_EMPTY)

    # Inject input var names into params so input_ref fields can display them
    p = dict(block.params)
    if block.input_vars:
        p["__input__"] = block.input_vars[0]
        if len(block.input_vars) >= 2:
            p["__left_input__"] = block.input_vars[0]
            p["__right_input__"] = block.input_vars[1]

    w = QWidget()
    w.setStyleSheet(_sentence_style())
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)

    for field in bt.sentence:
        val = get_field_value(p, field)
        if field.kind == "label":
            lay.addWidget(_lbl(field.text))
        elif field.kind == "text":
            wid = _le(field.param, str(val), field.placeholder, field.width)
            if not field.width:
                wid.setMinimumWidth(100)  # prevent collapse when many blocks
            lay.addWidget(wid, stretch=1 if not field.width else 0)
        elif field.kind == "combo":
            lay.addWidget(_cb(field.param, field.items or [], str(val), field.width))
        elif field.kind == "check":
            lay.addWidget(_chk(field.param, field.text, bool(val)))
        elif field.kind == "textarea":
            lay.addWidget(
                _te(field.param, str(val), field.placeholder, field.max_height)
            )
        elif field.kind == "input_ref":
            name = p.get(field.param, "df")
            lay.addWidget(_inp_lbl(name))
        elif field.kind == "stretch":
            lay.addStretch()

    # Append extra info labels (e.g. "+3 more")
    for extra in bt.extras:
        n = count_list(p, extra.list_key)
        if n > extra.threshold:
            remainder = n - extra.threshold
            lay.addWidget(_lbl(f"{extra.prefix}{remainder}{extra.suffix}"))

    # Always end with stretch if not already
    lay.addStretch()
    return w


def _collect_sentence_params(sentence: QWidget, block: BlockSpec) -> dict:
    """Generic collector — walks sentence children, reads values, writes
    them back into params using the FieldSpec path logic from blocks.py."""
    bt = BLOCKS.get(block.block_type)
    if bt is None:
        return dict(block.params)

    params = dict(block.params)

    # Build a lookup: objectName → FieldSpec
    field_map: dict[str, FieldSpec] = {}
    for f in bt.sentence:
        if f.param and f.kind in ("text", "combo", "check", "textarea"):
            field_map[f.param] = f

    for child in sentence.findChildren((QLineEdit, QTextEdit, QComboBox, QCheckBox)):
        name = child.objectName()
        if not name or name not in field_map:
            continue
        field = field_map[name]

        if isinstance(child, QCheckBox):
            set_field_value(params, field, child.isChecked())
        elif isinstance(child, QComboBox):
            set_field_value(params, field, child.currentText())
        elif isinstance(child, QTextEdit):
            set_field_value(params, field, child.toPlainText())
        elif isinstance(child, QLineEdit):
            set_field_value(params, field, child.text().strip())

    # Cleanup internal keys
    params.pop("__input__", None)
    params.pop("__left_input__", None)
    params.pop("__right_input__", None)
    return params


class _TitleLabel(QLabel):
    """Label that emits double_clicked without propagating to the card."""

    double_clicked = pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()


class BlockCard(QFrame):
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    duplicate_requested = pyqtSignal(str)
    move_up_requested = pyqtSignal(str)
    move_down_requested = pyqtSignal(str)
    label_changed = pyqtSignal(str, str)
    var_changed = pyqtSignal(str, str)
    card_clicked = pyqtSignal(str, str)
    params_changed = pyqtSignal(str, dict)
    reorder_requested = pyqtSignal(str, int)  # block_id, target_index

    def __init__(self, block: BlockSpec, step: int = 1, total: int = 1, parent=None):
        super().__init__(parent)
        self._block = block
        self.block_id = block.block_id
        self._block_type = block.block_type
        self._sentence = None
        self._label_edit = None
        self._var_edit = None
        self._title_lbl = None
        self._color = ""
        self._drag_start = None
        bt = BLOCKS.get(block.block_type)
        self._color = bt.color if bt else "#444466"
        icon = bt.icon if bt else "\u2b1a"

        self._apply_card_style()
        self.setMinimumHeight(84)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Fade-in animation on creation
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)
        self._fade_in = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_in.setDuration(180)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        QTimer.singleShot(30, self._fade_in.start)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 9, 10, 9)
        outer.setSpacing(5)

        # Row 1: step badge + icon + editable label + buttons
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        t = theme.tokens()
        step_lbl = QLabel(f"{step}")
        step_lbl.setFixedSize(26, 26)
        step_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step_lbl.setStyleSheet(
            f"background: {t['card_overlay']}; color: {t['card_text']};"
            f" border-radius: 13px; font-size: 12px; font-weight: bold;"
        )
        row1.addWidget(step_lbl)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 18px; background: transparent;")
        row1.addWidget(icon_lbl)

        # Editable label (double-click to rename)
        self._title_lbl = _TitleLabel(
            f"<b style='font-size:14px; color:{t['card_text']}'>{block.label}</b>"
        )
        self._title_lbl.setStyleSheet("background: transparent;")
        self._title_lbl.double_clicked.connect(self._start_edit)
        row1.addWidget(self._title_lbl)

        # Inline label editor (hidden, shown on double-click)
        self._label_edit = QLineEdit(block.label)
        self._label_edit.setVisible(False)
        self._label_edit.returnPressed.connect(self._finish_edit)
        self._label_edit.installEventFilter(self)
        row1.addWidget(self._label_edit)

        # Editable output variable name
        self._var_edit = QLineEdit(block.output_var)
        self._var_edit.setFixedWidth(74)
        self._var_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._var_edit.setToolTip(
            "Output variable name — referenced by downstream blocks"
        )
        self._var_edit.editingFinished.connect(self._on_var_changed)
        row1.addWidget(self._var_edit)
        row1.addStretch()

        # Buttons
        btn_style = self._card_btn_style()
        for text, slot, tooltip in [
            ("\u25b2", self._on_move_up, "Move up"),
            ("\u25bc", self._on_move_down, "Move down"),
            ("\u29c9", self._on_duplicate, "Duplicate"),
            ("\u2699", self._on_edit, "Full editor"),
        ]:
            btn = QPushButton(text)
            btn.setFixedSize(28 if text != "\u2699" else 34, 28)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(slot)
            row1.addWidget(btn)

        del_btn = QPushButton("\u2715")
        del_btn.setFixedSize(28, 28)
        del_btn.setToolTip("Delete")
        del_btn.setStyleSheet(self._card_del_style())
        del_btn.clicked.connect(self._on_delete)
        row1.addWidget(del_btn)
        outer.addLayout(row1)

        # Row 2: the sentence (replaces old summary line)
        self._sentence = _build_sentence(block)
        self._sentence.setStyleSheet(_sentence_style())
        outer.addWidget(self._sentence)

        # Wire change events from sentence widgets
        for child in self._sentence.findChildren(
            (QLineEdit, QComboBox, QCheckBox, QTextEdit)
        ):
            if isinstance(child, QLineEdit):
                child.editingFinished.connect(self._on_sentence_changed)
            elif isinstance(child, QComboBox):
                child.currentTextChanged.connect(lambda _: self._on_sentence_changed())
            elif isinstance(child, QCheckBox):
                child.toggled.connect(lambda _: self._on_sentence_changed())

        # Validation badge (hidden until set_warnings is called)
        self._badge = QLabel("")
        self._badge.setStyleSheet("background: transparent; font-size: 11px;")
        self._badge.setVisible(False)
        outer.addWidget(self._badge)

    # ── theme helpers ─────────────────────────────────────

    def _apply_card_style(self) -> None:
        t = theme.tokens()
        self.setStyleSheet(
            f"BlockCard {{ background: {self._color}; border-radius: 10px;"
            f" border: 1px solid {t['card_border']}; }}"
            f"BlockCard:hover {{ border: 1px solid {t['card_border_hover']};"
            f" background: {self._color}; }}"
        )
        if self._label_edit is not None:
            self._label_edit.setStyleSheet(
                f"QLineEdit {{ background: {t['card_overlay']}; color: {t['card_text']};"
                f" border: 1px solid {t['card_overlay_focus']};"
                f" border-radius: 4px; padding: 2px 6px; font-size: 14px;"
                f" font-weight: bold; }}"
            )
        if self._var_edit is not None:
            self._var_edit.setStyleSheet(
                f"QLineEdit {{ background: {t['card_overlay']}; color: {t['card_input_ref']};"
                f" border: 1px solid {t['card_border']}; border-radius: 4px;"
                f" padding: 2px 4px; font-size: 11px; font-weight: bold; }}"
                f"QLineEdit:focus {{ border: 1px solid {t['card_overlay_focus']};"
                f" color: {t['card_text']}; }}"
            )
        if self._sentence is not None:
            self._sentence.setStyleSheet(_sentence_style())
        if self._title_lbl is not None:
            self._refresh_title()

    def _card_btn_style(self) -> str:
        t = theme.tokens()
        return (
            f"QPushButton {{ background: {t['card_btn_bg']}; color: {t['card_text']};"
            f" border: none; border-radius: 5px; font-size: 13px; }}"
            f" QPushButton:hover {{ background: {t['card_btn_hover']}; }}"
        )

    def _card_del_style(self) -> str:
        t = theme.tokens()
        return (
            f"QPushButton {{ background: {t['card_del_bg']}; color: {t['card_del_text']};"
            f" border: none; border-radius: 5px; font-size: 13px; }}"
            f" QPushButton:hover {{ background: {t['card_del_hover']}; }}"
        )

    # ── validation badge ──────────────────────────────────

    def set_warnings(self, msgs: list[dict]):
        if not msgs:
            self._badge.setVisible(False)
            return
        t = theme.tokens()
        level = "error" if any(m["level"] == "error" for m in msgs) else "warning"
        icon = "\u26d4" if level == "error" else "\u26a0\ufe0f"
        color = t["danger"] if level == "error" else t["warning"]
        tooltip = "\n".join(f"\u2022 {m['message']}" for m in msgs)
        self._badge.setText(
            f"<span style='color:{color}'>{icon} {msgs[0]['message']}</span>"
        )
        self._badge.setToolTip(tooltip)
        self._badge.setVisible(True)

    # ── sentence change handler ───────────────────────────

    def _on_sentence_changed(self):
        """Collect params from the sentence widgets and emit."""
        if self._sentence is None:
            return
        new_params = _collect_sentence_params(self._sentence, self._block)
        self._block.params = new_params
        self.params_changed.emit(self.block_id, new_params)

    # ── inline label editing ──────────────────────────────

    def _start_edit(self):
        self._title_lbl.setVisible(False)
        self._label_edit.setText(self._block.label)
        self._label_edit.setVisible(True)
        self._label_edit.setFocus()
        self._label_edit.selectAll()

    def _finish_edit(self):
        new_label = self._label_edit.text().strip()
        if new_label and new_label != self._block.label:
            self._block.label = new_label
            self.label_changed.emit(self.block_id, new_label)
            self._refresh_title()
        self._cancel_edit()

    def _cancel_edit(self):
        self._label_edit.setVisible(False)
        self._title_lbl.setVisible(True)

    def _refresh_title(self):
        t = theme.tokens()
        self._title_lbl.setText(
            f"<b style='font-size:14px; color:{t['card_text']}'>{self._block.label}</b>"
        )

    # ── output variable rename ────────────────────────────

    def _on_var_changed(self):
        """Rename the output variable from the inline editor."""
        new_var = self._var_edit.text().strip()
        if new_var and new_var != self._block.output_var:
            self._block.output_var = new_var
            self.var_changed.emit(self.block_id, new_var)

    def eventFilter(self, obj, event):
        if obj is self._label_edit:
            if event.type() == QEvent.Type.FocusOut:
                QTimer.singleShot(100, self._cancel_edit)
                return False
            if (
                event.type() == QEvent.Type.KeyPress
                and event.key() == Qt.Key.Key_Escape
            ):
                self._cancel_edit()
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        self.card_clicked.emit(self.block_id, self._block_type)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self._drag_start is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            delta = (event.position().toPoint() - self._drag_start).manhattanLength()
            if delta > 10:
                from PyQt6.QtCore import QMimeData
                from PyQt6.QtGui import QDrag

                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(self.block_id)
                drag.setMimeData(mime)
                drag.exec(Qt.DropAction.MoveAction)
                return
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.edit_requested.emit(self.block_id)
        super().mouseDoubleClickEvent(event)

    def _on_move_up(self):
        self.move_up_requested.emit(self.block_id)

    def _on_move_down(self):
        self.move_down_requested.emit(self.block_id)

    def _on_duplicate(self):
        self.duplicate_requested.emit(self.block_id)

    def _on_edit(self):
        self.edit_requested.emit(self.block_id)

    def _on_delete(self):
        self.delete_requested.emit(self.block_id)
