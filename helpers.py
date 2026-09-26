"""
Shared helpers — operator lists, condition builders, result builders.

Used by both codegen and editor widgets.  Zero UI imports.
"""

from __future__ import annotations

import re as _re

# ── Operator constants ────────────────────────────────────────
OPERATORS = [
    "==",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "isNull",
    "isNotNull",
    "contains",
    "startswith",
    "endswith",
]

LOGICAL_OPS = ["AND", "OR"]
VALUE_TYPES = ["literal", "column"]
RESULT_TYPES = ["literal", "column", "expression"]


# ── Tiny utilities ───────────────────────────────────────────


def q(s) -> str:
    """Return ``s`` as a safely-quoted Python string literal.

    Handles embedded quotes / backslashes so user values can never break
    or inject into the generated script.
    """
    return repr("" if s is None else str(s))


_IDENT_RE = _re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def is_valid_ident(name: str) -> bool:
    """True if ``name`` is a usable Python identifier."""
    return bool(_IDENT_RE.match(str(name or "").strip()))


def is_numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def build_condition_expr(conditions: list[dict]) -> str:
    """Build a PySpark boolean expression from condition dicts.

    Each dict: {column, operator, value, value_type, logical_op?}
    Returns e.g.  (F.col("x") > 10) & (F.col("y") == "hi")
    """
    parts: list[str] = []
    for cond in conditions:
        col = cond.get("column", "")
        if not col:
            continue
        op = cond.get("operator", "==")
        col_expr = f"F.col({q(col)})"

        if op == "isNull":
            single = f"{col_expr}.isNull()"
        elif op == "isNotNull":
            single = f"{col_expr}.isNotNull()"
        elif op in ("contains", "startswith", "endswith"):
            single = f"{col_expr}.{op}({q(cond.get('value', ''))})"
        else:
            val = cond.get("value", "")
            val_type = cond.get("value_type", "literal")
            if val_type == "column":
                val_expr = f"F.col({q(val)})"
            elif is_numeric(val):
                val_expr = val
            else:
                val_expr = q(val)
            single = f"({col_expr} {op} {val_expr})"

        if not parts:
            parts.append(single)
        else:
            logical = cond.get("logical_op") or "AND"
            connector = "&" if logical == "AND" else "|"
            parts.append(f" {connector} {single}")

    return "".join(parts)


def build_result_expr(value: str, result_type: str) -> str:
    """Build the RHS of a WHEN / OTHERWISE."""
    if result_type == "column":
        return f"F.col({q(value)})"
    if result_type == "expression":
        return value
    if is_numeric(value):
        return value
    return f"F.lit({q(value)})"
