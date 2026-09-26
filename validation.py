"""
Pipeline validation — warns about incomplete or nonsensical blocks.

Returns a list of {level, message} dicts per block.
level: "error" (broken code), "warning" (probably unintentional), "ok".

Rules are defined in blocks.py — this module just evaluates them.
"""

from __future__ import annotations

from blocks import BLOCKS
from models import BlockSpec


def validate_block(block: BlockSpec) -> list[dict]:
    """Return validation messages for a single block.  Empty list = all good."""
    bt = BLOCKS.get(block.block_type)
    if bt is None:
        return []
    msgs: list[dict] = []
    p = block.params
    for rule in bt.validation:
        failed = False
        if rule.check_fn:
            failed = not rule.check_fn(p)
        elif rule.param_key:
            val = p.get(rule.param_key)
            if isinstance(val, (list, str)):
                failed = not val
            else:
                failed = val is None or val == ""
        if failed:
            msgs.append({"level": rule.level, "message": rule.message})
    return msgs


def validate_pipeline(blocks: list[BlockSpec]) -> dict[str, list[dict]]:
    """Return {block_id: [messages]} for blocks with warnings/errors."""
    result: dict[str, list[dict]] = {}
    for b in blocks:
        msgs = validate_block(b)
        if msgs:
            result[b.block_id] = msgs
    return result


def worst_level(msgs: list[dict]) -> str:
    """Return the worst severity level in a list of messages."""
    for m in msgs:
        if m["level"] == "error":
            return "error"
    for m in msgs:
        if m["level"] == "warning":
            return "warning"
    return "ok"
