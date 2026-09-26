"""Plain-English pipeline explainer — turns blocks into readable descriptions.

Pure data module, zero UI dependencies.  Designed for freshers who can build
a pipeline visually but don't yet read PySpark code fluently.

    explain_block(block)   → "Keep only rows where amount > 0."
    explain_pipeline(state) → full walkthrough + data-flow + summary
"""

from __future__ import annotations

from models import BlockSpec, PipelineState


def _q(val) -> str:
    """Display a value nicely (strip quotes for human reading)."""
    s = str(val).strip() if val is not None else ""
    return s if s else "(not set)"


def _list(items, conj="and") -> str:
    """Join a list into readable English: 'a, b and c'."""
    items = [str(x) for x in items if str(x).strip()]
    if not items:
        return "(none)"
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conj} {items[1]}"
    return ", ".join(items[:-1]) + f" {conj} {items[-1]}"


def _op_text(op: str) -> str:
    """Convert a filter operator to plain English."""
    mapping = {
        "==": "equals",
        "!=": "does not equal",
        ">": "is greater than",
        ">=": "is greater than or equal to",
        "<": "is less than",
        "<=": "is less than or equal to",
        "isNull": "is null (empty)",
        "isNotNull": "is not null",
        "contains": "contains",
        "startswith": "starts with",
        "endswith": "ends with",
    }
    return mapping.get(op, op)


def explain_block(block: BlockSpec) -> str:
    """Return a plain-English sentence describing what this block does.

    Uses the block's actual parameters — not just the generic type help —
    so a filter block with column='amount', op='>', value='0' becomes
    'Keep only rows where amount is greater than 0.'
    """
    bt = block.block_type
    p = block.params
    out = block.output_var
    inp = block.input_vars[0] if block.input_vars else "(nothing)"

    if bt in ("read_csv", "read_parquet", "read_json"):
        fmt = p.get("format", bt.replace("read_", ""))
        path = _q(p.get("path"))
        extras = []
        if fmt == "csv":
            if p.get("header", True):
                extras.append("the first row is a header")
            if p.get("infer_schema", True):
                extras.append("Spark will guess column types automatically")
            delim = p.get("delimiter", ",")
            if delim != ",":
                extras.append(f"columns are separated by '{delim}'")
        extra_str = f" ({', '.join(extras)})" if extras else ""
        return f"Load a {fmt.upper()} file from {path}{extra_str} into a DataFrame called '{out}'."

    if bt in ("write_csv", "write_parquet"):
        fmt = p.get("format", bt.replace("write_", ""))
        path = _q(p.get("path"))
        mode = p.get("mode", "overwrite")
        mode_text = {
            "overwrite": "overwriting any existing files",
            "append": "adding to existing files",
            "ignore": "skipping if the file already exists",
            "error": "raising an error if the file exists",
        }.get(mode, mode)
        return f"Save '{inp}' to {path} as {fmt.upper()} ({mode_text})."

    if bt == "select":
        cols = p.get("columns", [])
        if not cols:
            return f"Pass '{inp}' through unchanged (no columns selected)."
        return f"Keep only these columns from '{inp}': {_list(cols)}. Result → '{out}'."

    if bt == "drop":
        cols = p.get("columns", [])
        if not cols:
            return f"Pass '{inp}' through unchanged (no columns dropped)."
        return f"Remove these columns from '{inp}': {_list(cols)}. Result → '{out}'."

    if bt == "rename":
        mappings = p.get("mappings", [])
        if not mappings:
            return f"Pass '{inp}' through unchanged (no columns renamed)."
        parts = [f"'{m.get('old', '?')}' → '{m.get('new', '?')}'" for m in mappings]
        return f"Rename columns in '{inp}': {_list(parts)}. Result → '{out}'."

    if bt == "filter":
        conds = p.get("conditions", [])
        if not conds:
            return f"Pass '{inp}' through unchanged (no filter conditions)."
        parts = []
        for i, c in enumerate(conds):
            col = _q(c.get("column"))
            op = _op_text(c.get("operator", "=="))
            val = _q(c.get("value")) if c.get("operator") not in ("isNull", "isNotNull") else ""
            logic = c.get("logical_op", "AND")
            clause = f"{col} {op}" + (f" {val}" if val else "")
            if i == 0:
                parts.append(clause)
            else:
                parts.append(f"{logic} {clause}")
        return f"Keep only rows from '{inp}' where: {' '.join(parts)}. Result → '{out}'."

    if bt == "cast":
        casts = p.get("casts", [])
        if not casts:
            return f"Pass '{inp}' through unchanged (no type casts)."
        parts = [f"{c.get('column', '?')} → {c.get('target_type', '?')}" for c in casts]
        return f"Change column types in '{inp}': {_list(parts)}. Result → '{out}'."

    if bt == "when_otherwise":
        branches = p.get("branches", [])
        out_col = p.get("output_column", "new_col")
        if not branches:
            return f"Pass '{inp}' through unchanged (no conditions defined)."
        n = len(branches)
        otherwise = p.get("otherwise_value", "null")
        otherwise_type = p.get("otherwise_type", "null")
        if otherwise_type == "null":
            otherwise_text = "null"
        else:
            otherwise_text = f"'{otherwise}'"
        return (
            f"Create a new column '{out_col}' in '{inp}' with {n} "
            f"{'condition' if n == 1 else 'conditions'} "
            f"(otherwise = {otherwise_text}). Result → '{out}'."
        )

    if bt == "join":
        left = block.input_vars[0] if len(block.input_vars) >= 1 else "(left)"
        right = block.input_vars[1] if len(block.input_vars) >= 2 else "(right)"
        jtype = p.get("join_type", "inner")
        keys = p.get("join_keys", [])
        broadcast = p.get("broadcast_right", False)
        key_text = ", ".join(
            f"{k.get('left', '?')} = {k.get('right', '?')}" for k in keys
        ) if keys else "(no keys — cross join)"
        bc_text = " (broadcast right table for speed)" if broadcast else ""
        return (
            f"Join '{left}' with '{right}' on [{key_text}] using an "
            f"{jtype} join{bc_text}. Result → '{out}'."
        )

    if bt == "groupby_agg":
        group_cols = p.get("group_by_cols", [])
        aggs = p.get("aggregations", [])
        if not group_cols and not aggs:
            return f"Pass '{inp}' through unchanged (no grouping or aggregations)."
        group_text = f"grouped by {_list(group_cols)}" if group_cols else "without grouping"
        agg_parts = []
        for a in aggs:
            fn = a.get("function", "count")
            col = a.get("column", "*")
            alias = a.get("alias", f"{fn}_{col}")
            agg_parts.append(f"{fn}({col}) as '{alias}'")
        agg_text = _list(agg_parts) if agg_parts else "(no aggregations)"
        return f"Summarize '{inp}', {group_text}, calculating {agg_text}. Result → '{out}'."

    if bt == "window":
        func = p.get("function", "row_number")
        out_col = p.get("output_column", "new_col")
        partition = p.get("partition_by", [])
        order_by = p.get("order_by", [])
        parts = []
        if partition:
            parts.append(f"partitioned by {_list(partition)}")
        if order_by:
            order_parts = [f"{o.get('column', '?')} {o.get('direction', 'asc')}" for o in order_by]
            parts.append(f"ordered by {_list(order_parts)}")
        desc = ", ".join(parts) if parts else "no partitioning or ordering"
        return (
            f"Calculate {func}() over a window ({desc}) for '{inp}', "
            f"storing the result in column '{out_col}'. Result → '{out}'."
        )

    if bt == "string_op":
        op = p.get("operation", "upper")
        col = _q(p.get("col"))
        out_col = p.get("output_column", col)
        op_text = {
            "upper": "convert to UPPERCASE",
            "lower": "convert to lowercase",
            "trim": "remove leading/trailing spaces",
            "ltrim": "remove leading spaces",
            "rtrim": "remove trailing spaces",
            "length": "get the length (number of characters)",
            "reverse": "reverse the string",
            "initcap": "capitalize the first letter of each word",
            "substring": "extract a substring",
            "split": "split into parts",
            "concat": "concatenate multiple columns",
            "concat_ws": "concatenate with a separator",
            "regexp_replace": "replace text matching a pattern",
            "lpad": "pad on the left",
            "rpad": "pad on the right",
            "translate": "translate characters",
        }.get(op, f"apply {op}")
        return f"{op_text} on column '{col}' from '{inp}', store in '{out_col}'. Result → '{out}'."

    if bt == "date_op":
        op = p.get("operation", "year")
        col = _q(p.get("col")) if op not in ("current_date", "current_timestamp") else "(no input needed)"
        out_col = p.get("output_column", col)
        op_text = {
            "current_date": "get today's date",
            "current_timestamp": "get the current date and time",
            "to_date": "convert to a date",
            "to_timestamp": "convert to a timestamp",
            "date_add": "add days to a date",
            "date_sub": "subtract days from a date",
            "datediff": "calculate the difference between two dates (in days)",
            "months_between": "calculate months between two dates",
            "add_months": "add months to a date",
            "year": "extract the year",
            "month": "extract the month",
            "dayofmonth": "extract the day of month",
            "dayofweek": "extract the day of week",
            "dayofyear": "extract the day of year",
            "hour": "extract the hour",
            "minute": "extract the minute",
            "second": "extract the second",
            "last_day": "get the last day of the month",
            "trunc": "truncate to a unit (e.g. month, year)",
            "date_format": "format as a string",
        }.get(op, f"apply {op}")
        return f"{op_text} on column '{col}' from '{inp}', store in '{out_col}'. Result → '{out}'."

    if bt == "custom":
        code = p.get("code", "")
        if not code.strip():
            return "Custom code block (empty — does nothing)."
        first_line = code.strip().split("\n")[0][:80]
        return f"Run custom PySpark code: {first_line}..."

    return f"Unknown block type '{bt}'."


def _category(block_type: str) -> str:
    """Classify a block for the pipeline summary."""
    if block_type.startswith("read_"):
        return "Read"
    if block_type.startswith("write_"):
        return "Write"
    if block_type in ("select", "drop", "rename", "cast"):
        return "Column transform"
    if block_type in ("filter", "when_otherwise"):
        return "Row filter"
    if block_type in ("string_op", "date_op"):
        return "Expression"
    if block_type in ("join", "groupby_agg", "window"):
        return "Aggregation / Join"
    if block_type == "custom":
        return "Custom"
    return "Other"


def data_flow(state: PipelineState) -> str:
    """Return a text-based data-flow diagram: 'raw → filtered → summary → (write)'."""
    if not state.blocks:
        return "(empty pipeline)"
    parts = []
    for b in state.blocks:
        if b.block_type.startswith("write_"):
            inp = b.input_vars[0] if b.input_vars else "?"
            parts.append(f"{inp} → (save to {_q(b.params.get('path'))})")
        elif b.block_type.startswith("read_"):
            parts.append(f"(file) → {b.output_var}")
        elif b.block_type == "join":
            left = b.input_vars[0] if len(b.input_vars) >= 1 else "?"
            right = b.input_vars[1] if len(b.input_vars) >= 2 else "?"
            parts.append(f"{left} + {right} → {b.output_var}")
        else:
            inp = b.input_vars[0] if b.input_vars else "?"
            parts.append(f"{inp} → {b.output_var}")
    return "  ".join(parts)


def pipeline_summary(state: PipelineState) -> dict:
    """Return a summary dict with counts by category, for display."""
    counts: dict[str, int] = {}
    for b in state.blocks:
        cat = _category(b.block_type)
        counts[cat] = counts.get(cat, 0) + 1
    return {
        "total_blocks": len(state.blocks),
        "categories": counts,
        "app_name": state.spark_app_name,
        "has_read": any(b.block_type.startswith("read_") for b in state.blocks),
        "has_write": any(b.block_type.startswith("write_") for b in state.blocks),
    }


def explain_pipeline(state: PipelineState) -> list[dict]:
    """Full walkthrough — returns a list of step dicts for the dialog to render.

    Each dict: {step, label, type, description, flow}
    """
    steps = []
    for i, block in enumerate(state.blocks):
        steps.append({
            "step": i + 1,
            "label": block.label,
            "type": block.block_type,
            "category": _category(block.block_type),
            "description": explain_block(block),
            "output_var": block.output_var,
            "input_vars": block.input_vars,
        })
    return steps
