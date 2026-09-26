"""
Data model — pure dataclasses, zero UI dependencies.

BlockSpec   — one visual block (unit of state).
PipelineState — ordered list of blocks + app metadata + schema registry.
"""

from __future__ import annotations

import dataclasses
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from blocks import BLOCKS
from schema import SchemaRegistry


@dataclass
class BlockSpec:
    block_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    block_type: str = ""
    label: str = ""
    output_var: str = "df"
    params: dict[str, Any] = field(default_factory=dict)
    input_vars: list[str] = field(default_factory=list)


@dataclass
class PipelineState:
    blocks: list[BlockSpec] = field(default_factory=list)
    spark_app_name: str = "MyPySparkApp"
    schemas: SchemaRegistry = field(default_factory=SchemaRegistry)

    # ── mutation ──────────────────────────────────────────

    def add_block(self, block: BlockSpec) -> None:
        self.blocks.append(block)
        self._recalc_input_vars()

    def remove_block(self, block_id: str) -> None:
        self.blocks = [b for b in self.blocks if b.block_id != block_id]
        self._recalc_input_vars()

    def move_block(self, block_id: str, direction: int) -> None:
        idx = next(i for i, b in enumerate(self.blocks) if b.block_id == block_id)
        new_idx = max(0, min(len(self.blocks) - 1, idx + direction))
        self.blocks.insert(new_idx, self.blocks.pop(idx))
        self._recalc_input_vars()

    def get_block(self, block_id: str) -> BlockSpec | None:
        return next((b for b in self.blocks if b.block_id == block_id), None)

    def recalc_input_vars(self) -> None:
        """Public entry point for auto-wiring (see ``_recalc_input_vars``)."""
        self._recalc_input_vars()

    def _recalc_input_vars(self) -> None:
        """Auto-wire blocks based on position and declared input_count.

        Only updates blocks whose input_vars are empty or clearly broken
        (pointing to non-existent outputs).  Preserves existing valid wiring.
        """
        valid_outputs = {b.output_var for b in self.blocks}
        for i, block in enumerate(self.blocks):
            if block.input_vars and all(v in valid_outputs for v in block.input_vars):
                continue
            bt = BLOCKS.get(block.block_type)
            count = bt.input_count if bt else 1
            if count == 0:
                block.input_vars = []
            elif count == 2:
                precursors = self.blocks[:i]
                block.input_vars = [b.output_var for b in precursors[-2:]]
            else:
                block.input_vars = [self.blocks[i - 1].output_var] if i > 0 else []

    # ── serialization ─────────────────────────────────────

    def to_json(self, *, indent: bool = True) -> str:
        """Serialize to JSON.  ``indent=True`` for save files (human-readable),
        ``indent=False`` for undo snapshots (fast, compact)."""
        data = dataclasses.asdict(self)
        data["schemas"] = self.schemas.to_dict()
        return json.dumps(data, indent=2 if indent else None)

    def to_snapshot(self) -> str:
        """Fast compact JSON snapshot for undo/redo.

        Bypasses ``dataclasses.asdict`` (which deep-copies every nested
        dict) and serializes block fields directly — ~2x faster than
        ``to_json(indent=False)`` for large pipelines.
        """
        return json.dumps({
            "spark_app_name": self.spark_app_name,
            "blocks": [
                {
                    "block_id": b.block_id,
                    "block_type": b.block_type,
                    "label": b.label,
                    "output_var": b.output_var,
                    "params": b.params,
                    "input_vars": b.input_vars,
                }
                for b in self.blocks
            ],
            "schemas": self.schemas.to_dict(),
        })

    @staticmethod
    def from_json(text: str) -> PipelineState:
        data = json.loads(text)
        state = PipelineState(spark_app_name=data.get("spark_app_name", "MyPySparkApp"))
        state.schemas = SchemaRegistry.from_dict(data.get("schemas", {}))
        # Only keep fields BlockSpec knows about — ignore legacy/extra keys so
        # older saved files don't crash with a TypeError.
        known = {f.name for f in dataclasses.fields(BlockSpec)}
        for b in data.get("blocks", []):
            filtered = {k: v for k, v in b.items() if k in known}
            state.blocks.append(BlockSpec(**filtered))
        state._recalc_input_vars()
        return state
