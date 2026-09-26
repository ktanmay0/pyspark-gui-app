"""
Pipeline Controller — owns state, undo/redo, and file I/O.

Emits signals so the UI can react without knowing business logic.
"""

from __future__ import annotations

import copy
import json
import os
import uuid

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from codegen import generate
from helpers import is_valid_ident
from models import BlockSpec, PipelineState

_UNDO_LIMIT = 50
_CODEGEN_DEBOUNCE_MS = 150
_UNDO_COALESCE_MS = 400


def _next_var(state: PipelineState) -> str:
    existing = {b.output_var for b in state.blocks}
    i = 1
    while f"df{i}" in existing:
        i += 1
    return f"df{i}"


def _safe_generate(state: PipelineState) -> str:
    """Wrapper that catches codegen errors so the UI never crashes."""
    try:
        return generate(state)
    except Exception as exc:
        return f"# ⛔ Code generation error: {exc}\n# Check block parameters for invalid values."


class PipelineController(QObject):
    """Single source of truth for pipeline state + undo/redo + file ops."""

    # Emitted whenever the pipeline list changes (canvas rebuild needed)
    pipeline_changed = pyqtSignal()
    # Emitted with new code after any state change (debounced)
    code_changed = pyqtSignal(str)
    # Emitted for status-bar messages
    status = pyqtSignal(str)
    # Emitted when the dirty flag changes (for the title * indicator)
    dirty_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = PipelineState()
        self._undo_stack: list[str] = []
        self._redo_stack: list[str] = []
        self._current_file: str | None = None
        self._file_mtime: float = 0.0
        self._dirty = False

        # Debounce timer for code generation — coalesces rapid changes so
        # codegen + preview re-highlight run at most once per 150ms.
        self._codegen_timer = QTimer(self)
        self._codegen_timer.setSingleShot(True)
        self._codegen_timer.setInterval(_CODEGEN_DEBOUNCE_MS)
        self._codegen_timer.timeout.connect(self._flush_codegen)

        # Undo coalescing — rapid successive edits (combo changes, checkbox
        # toggles, field edits) within 400ms collapse into a single undo
        # entry instead of one-per-edit.
        self._coalescing = False
        self._coalesce_timer = QTimer(self)
        self._coalesce_timer.setSingleShot(True)
        self._coalesce_timer.setInterval(_UNDO_COALESCE_MS)
        self._coalesce_timer.timeout.connect(self._end_coalesce)

    # ── dirty flag ────────────────────────────────────────

    @property
    def is_dirty(self) -> bool:
        """True if there are unsaved changes since the last save/load."""
        return self._dirty

    def _mark_dirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            self.dirty_changed.emit(True)

    def _mark_clean(self) -> None:
        if self._dirty:
            self._dirty = False
            self.dirty_changed.emit(False)

    # ── undo / redo ────────────────────────────────────────

    def _push_undo(self, *, coalesce: bool = False) -> None:
        """Snapshot current state for undo.

        With ``coalesce=True`` (used by rapid field edits), successive
        calls within ``_UNDO_COALESCE_MS`` skip the snapshot — the
        pre-edit state is already on the stack from the first call.
        Structural ops pass ``coalesce=False`` to force a fresh entry.
        """
        if coalesce and self._coalescing:
            self._mark_dirty()
            return  # pre-edit state already captured at window start
        # Force-end any active coalescing window for structural ops.
        self._coalescing = False
        self._coalesce_timer.stop()
        self._undo_stack.append(self.state.to_snapshot())
        if len(self._undo_stack) > _UNDO_LIMIT:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._mark_dirty()
        if coalesce:
            self._coalescing = True
            self._coalesce_timer.start()

    def _end_coalesce(self) -> None:
        self._coalescing = False

    def undo(self) -> None:
        if not self._undo_stack:
            self.status.emit("Nothing to undo")
            return
        self._redo_stack.append(self.state.to_snapshot())
        try:
            self.state = PipelineState.from_json(self._undo_stack.pop())
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            self.status.emit(f"Undo failed: {exc}")
            return
        self._mark_dirty()
        self._emit_all("Undo", immediate=True)

    def redo(self) -> None:
        if not self._redo_stack:
            self.status.emit("Nothing to redo")
            return
        self._undo_stack.append(self.state.to_snapshot())
        try:
            self.state = PipelineState.from_json(self._redo_stack.pop())
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            self.status.emit(f"Redo failed: {exc}")
            return
        self._mark_dirty()
        self._emit_all("Redo", immediate=True)

    # ── block mutations ────────────────────────────────────

    def add_block(self, block_type: str, label: str) -> BlockSpec:
        self._push_undo()
        block = BlockSpec(
            block_type=block_type,
            label=label,
            output_var=_next_var(self.state),
        )
        self.state.add_block(block)
        self._emit_all(f"Added {label}")
        return block

    def update_block(self, block_id: str, new_params: dict) -> bool:
        block = self.state.get_block(block_id)
        if block is None:
            return False
        self._push_undo()
        block.params = new_params
        self._emit_all(f"Updated {block.label}")
        return True

    def update_params_quiet(self, block_id: str, new_params: dict) -> bool:
        """Update params without rebuilding the canvas (only code preview).

        Uses undo coalescing so rapid edits collapse into one undo entry,
        and debounced codegen so the preview updates at most once per 150ms.
        """
        block = self.state.get_block(block_id)
        if block is None:
            return False
        self._push_undo(coalesce=True)
        block.params = new_params
        self._schedule_codegen()
        return True

    def rename_block(self, block_id: str, new_label: str) -> bool:
        block = self.state.get_block(block_id)
        if block is None:
            return False
        self._push_undo(coalesce=True)
        block.label = new_label
        self._schedule_codegen()
        self.status.emit(f"Renamed to '{new_label}'")
        return True

    def rename_var(self, block_id: str, new_var: str) -> bool:
        """Rename output variable and recalc downstream wiring."""
        block = self.state.get_block(block_id)
        if block is None:
            return False
        new_var = new_var.strip()
        if not is_valid_ident(new_var):
            self.status.emit(
                "Invalid variable name — use letters, digits and '_' only"
            )
            return False
        self._push_undo()
        block.output_var = new_var
        self.state.recalc_input_vars()
        self._emit_all(f"Variable renamed to '{new_var}'")
        return True

    def remove_block(self, block_id: str) -> None:
        block = self.state.get_block(block_id)
        name = block.label if block else "block"
        self._push_undo()
        self.state.remove_block(block_id)
        self._emit_all(f"Deleted {name}")

    def duplicate_block(self, block_id: str) -> None:
        """Deep-copy a block and insert it right after the original."""
        block = self.state.get_block(block_id)
        if block is None:
            return
        self._push_undo()
        new_block = copy.deepcopy(block)
        new_block.block_id = str(uuid.uuid4())
        new_block.output_var = _next_var(self.state)
        idx = next(i for i, b in enumerate(self.state.blocks) if b.block_id == block_id)
        self.state.blocks.insert(idx + 1, new_block)
        self.state.recalc_input_vars()
        self._emit_all(f"Duplicated {block.label}")

    def reorder_block(self, block_id: str, target_index: int) -> None:
        """Move a block to a new position in the pipeline."""
        block = self.state.get_block(block_id)
        if block is None or target_index < 0:
            return
        blocks = self.state.blocks
        old_idx = next(i for i, b in enumerate(blocks) if b.block_id == block_id)
        if old_idx == target_index:
            return  # no-op — don't pollute the undo stack
        self._push_undo()
        blocks.insert(target_index, blocks.pop(old_idx))
        self.state.recalc_input_vars()
        self._emit_all(f"Reordered {block.label}")

    def sort_pipeline(self) -> None:
        """Sort blocks by category: reads → transforms → writes."""
        order = {
            "read_csv": 0,
            "read_parquet": 0,
            "read_json": 0,
            "select": 1,
            "drop": 1,
            "rename": 1,
            "filter": 2,
            "cast": 2,
            "when_otherwise": 2,
            "string_op": 3,
            "date_op": 3,
            "join": 4,
            "groupby_agg": 4,
            "window": 4,
            "custom": 5,
            "write_csv": 6,
            "write_parquet": 6,
        }
        self._push_undo()
        self.state.blocks.sort(key=lambda b: order.get(b.block_type, 99))
        self.state.recalc_input_vars()
        self._emit_all("Pipeline sorted")

    def move_block(self, block_id: str, direction: int) -> None:
        self._push_undo()
        self.state.move_block(block_id, direction)
        self._emit_all()

    def update_schemas(self, schemas) -> None:
        self._push_undo()
        self.state.schemas = schemas
        self._emit_all("Schema updated")

    def set_app_name(self, name: str) -> bool:
        """Set the Spark application name (shown in generated code)."""
        name = name.strip()
        if not name or name == self.state.spark_app_name:
            return False
        self._push_undo(coalesce=True)
        self.state.spark_app_name = name
        self._schedule_codegen()
        self.status.emit(f"App name set to '{name}'")
        return True

    # ── file I/O ───────────────────────────────────────────

    @property
    def current_file(self) -> str | None:
        """Path of the file currently loaded/saved (None if never saved)."""
        return self._current_file

    def reload_current(self) -> None:
        """Reload the current file (used after external modification)."""
        if self._current_file:
            self.load_pipeline(self._current_file)

    def new_pipeline(self) -> None:
        self.state = PipelineState()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._current_file = None
        self._file_mtime = 0.0
        self._mark_clean()
        self._emit_all("New pipeline", immediate=True)

    def save_pipeline(self, path: str) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.state.to_json())
            self._current_file = path
            self._file_mtime = os.path.getmtime(path)
            self._mark_clean()
            self.status.emit(f"\u2713 Saved {path}")
        except OSError as exc:
            self.status.emit(f"Save failed: {exc}")

    def load_pipeline(self, path: str) -> None:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            self.state = PipelineState.from_json(text)
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._current_file = path
            self._file_mtime = os.path.getmtime(path)
            self._mark_clean()
            self._emit_all(f"\u2713 Loaded {path}", immediate=True)
        except json.JSONDecodeError as exc:
            self.status.emit(f"Invalid JSON: {exc}")
        except OSError as exc:
            self.status.emit(f"Load failed: {exc}")

    def export_script(self, path: str) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(_safe_generate(self.state))
            self.status.emit(f"\u2713 Exported {path}")
        except OSError as exc:
            self.status.emit(f"Export failed: {exc}")

    def copy_code(self) -> str:
        self._flush_codegen()
        return _safe_generate(self.state)

    def check_file_changed(self) -> bool:
        """Return True if the currently loaded file was modified externally."""
        if not self._current_file or not os.path.exists(self._current_file):
            return False
        try:
            return os.path.getmtime(self._current_file) > self._file_mtime + 0.5
        except OSError:
            return False

    # ── codegen debounce ──────────────────────────────────

    def _schedule_codegen(self) -> None:
        """Debounce code generation — restarts the timer so rapid changes
        coalesce into a single ``code_changed`` emission."""
        self._codegen_timer.start()

    def _flush_codegen(self) -> None:
        """Force immediate code generation if a debounced update is pending."""
        if self._codegen_timer.isActive():
            self._codegen_timer.stop()
        self.code_changed.emit(_safe_generate(self.state))

    # ── helpers ────────────────────────────────────────────

    def _emit_all(self, msg: str = "", *, immediate: bool = False) -> None:
        """Emit pipeline_changed (always immediate) + code_changed (debounced
        unless ``immediate=True`` for undo/redo/load)."""
        self.pipeline_changed.emit()
        if immediate:
            self._flush_codegen()
        else:
            self._schedule_codegen()
        if msg:
            self.status.emit(msg)

    def current_code(self) -> str:
        """Return current code immediately (flushes any pending debounce)."""
        self._flush_codegen()
        return _safe_generate(self.state)
