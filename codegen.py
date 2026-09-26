"""
Code generation engine — pure Python, zero UI dependencies.

Turns PipelineState -> complete PySpark script string.
Block-type-specific dispatch is in blocks.py. This module only
contains the generator functions and the top-level generate().
"""

from __future__ import annotations

from blocks import BLOCKS, IMP_F, IMP_S, IMP_T, IMP_W
from helpers import build_condition_expr, build_result_expr, is_numeric, q
from models import BlockSpec, PipelineState

# Deterministic import ordering (SparkSession first, then F/T/W).
_IMPORT_RANK = {IMP_S: 0, IMP_F: 1, IMP_T: 2, IMP_W: 3}


def _collect_imports(blocks: list[BlockSpec]) -> str:
    """Collect required PySpark imports from the block registry."""
    required: set[str] = {IMP_S}
    for b in blocks:
        bt = BLOCKS.get(b.block_type)
        if bt:
            required |= bt.imports
    ordered = sorted(required, key=lambda s: _IMPORT_RANK.get(s, 99))
    return "\n".join(ordered)


# ═══════════════════════════════════════════════════════════════
#  Per-block generators
# ═══════════════════════════════════════════════════════════════


def _gen_read(block: BlockSpec) -> str:
    p = block.params
    fmt = p.get("format", "csv")
    path = p.get("path", "")
    out = block.output_var
    opts: list[str] = []
    if fmt == "csv":
        if p.get("header", True):
            opts.append('header="true"')
        if p.get("infer_schema", True):
            opts.append('inferSchema="true"')
        delim = p.get("delimiter", ",")
        if delim != ",":
            opts.append(f"sep={q(delim)}")
    opts_str = ", ".join(opts)
    if opts_str:
        return f"{out} = spark.read.options({opts_str}).{fmt}({q(path)})"
    return f"{out} = spark.read.{fmt}({q(path)})"


def _gen_write(block: BlockSpec) -> str:
    p = block.params
    fmt = p.get("format", "parquet")
    path = p.get("path", "")
    mode = p.get("mode", "overwrite")
    inp = block.input_vars[0] if block.input_vars else "df"
    hdr = '.option("header", "true")' if fmt == "csv" and p.get("header", True) else ""
    return f"{inp}.write.mode({q(mode)}){hdr}.{fmt}({q(path)})"


def _gen_select(block: BlockSpec) -> str:
    cols = block.params.get("columns", [])
    inp = block.input_vars[0] if block.input_vars else "df"
    if not cols:
        return f"{block.output_var} = {inp}"
    return f"{block.output_var} = {inp}.select({', '.join(repr(c) for c in cols)})"


def _gen_drop(block: BlockSpec) -> str:
    cols = block.params.get("columns", [])
    inp = block.input_vars[0] if block.input_vars else "df"
    if not cols:
        return f"{block.output_var} = {inp}"
    return f"{block.output_var} = {inp}.drop({', '.join(repr(c) for c in cols)})"


def _gen_rename(block: BlockSpec) -> str:
    inp = block.input_vars[0] if block.input_vars else "df"
    out = block.output_var
    mappings = block.params.get("mappings", [])
    if not mappings:
        return f"{out} = {inp}"
    lines: list[str] = []
    for i, m in enumerate(mappings):
        src = inp if i == 0 else out
        old, new = m.get("old", ""), m.get("new", "")
        if old and new:
            lines.append(f"{out} = {src}.withColumnRenamed({q(old)}, {q(new)})")
    return "\n".join(lines) if lines else f"{out} = {inp}"


def _gen_filter(block: BlockSpec) -> str:
    inp = block.input_vars[0] if block.input_vars else "df"
    out = block.output_var
    conditions = block.params.get("conditions", [])
    if not conditions:
        return f"{out} = {inp}"
    return f"{out} = {inp}.filter({build_condition_expr(conditions)})"


def _gen_cast(block: BlockSpec) -> str:
    inp = block.input_vars[0] if block.input_vars else "df"
    out = block.output_var
    casts = block.params.get("casts", [])
    if not casts:
        return f"{out} = {inp}"
    lines: list[str] = []
    for i, c in enumerate(casts):
        src = inp if i == 0 else out
        col = c.get("column", "")
        t = c.get("target_type", "StringType")
        # Ensure type name ends with () for instantiation
        if t and not t.endswith(")"):
            t += "()"
        if col:
            lines.append(f"{out} = {src}.withColumn({q(col)}, F.col({q(col)}).cast({t}))")
    return "\n".join(lines) if lines else f"{out} = {inp}"


def _gen_when_otherwise(block: BlockSpec) -> str:
    p = block.params
    inp = block.input_vars[0] if block.input_vars else "df"
    out = block.output_var
    output_col = p.get("output_column", "new_col")
    branches = p.get("branches", [])
    otherwise_val = p.get("otherwise_value", "None")
    otherwise_type = p.get("otherwise_type", "null")
    if not branches:
        return f"{out} = {inp}"

    first = branches[0]
    first_conds = first.get("conditions", [])
    if not first_conds:
        return f"{out} = {inp}"

    chain = f"F.when({build_condition_expr(first_conds)}, {build_result_expr(first.get('result_value', ''), first.get('result_type', 'literal'))})"
    for branch in branches[1:]:
        branch_conds = branch.get("conditions", [])
        if not branch_conds:
            continue
        chain += f"\\\n        .when({build_condition_expr(branch_conds)}, {build_result_expr(branch.get('result_value', ''), branch.get('result_type', 'literal'))})"

    if otherwise_type == "null":
        otherwise_expr = "F.lit(None)"
    elif otherwise_type == "column":
        otherwise_expr = f"F.col({q(otherwise_val)})"
    elif is_numeric(otherwise_val):
        otherwise_expr = otherwise_val
    else:
        otherwise_expr = f"F.lit({q(otherwise_val)})"
    chain += f"\\\n        .otherwise({otherwise_expr})"
    return f"{out} = {inp}.withColumn({q(output_col)}, {chain})"


def _gen_join(block: BlockSpec) -> str:
    p = block.params
    left_df = block.input_vars[0] if len(block.input_vars) >= 1 else "df_left"
    right_df = block.input_vars[1] if len(block.input_vars) >= 2 else "df_right"
    out = block.output_var
    join_type = p.get("join_type", "inner")
    keys = p.get("join_keys", [])
    broadcast = p.get("broadcast_right", False)
    right_expr = f"F.broadcast({right_df})" if broadcast else right_df

    if not keys:
        return f"{out} = {left_df}.join({right_expr}, how={q(join_type)})"

    if len(keys) == 1:
        lk, rk = keys[0].get("left", ""), keys[0].get("right", "")
        if lk == rk and lk:
            join_cond = q(lk)
        elif lk and rk:
            join_cond = f"{left_df}[{q(lk)}] == {right_df}[{q(rk)}]"
        else:
            join_cond = ""
    else:
        parts = [
            f"({left_df}[{q(k['left'])}] == {right_df}[{q(k['right'])}])"
            for k in keys
            if k.get("left") and k.get("right")
        ]
        join_cond = " & ".join(parts) if parts else ""

    if not join_cond:
        return f"{out} = {left_df}.join({right_expr}, how={q(join_type)})"
    return f"{out} = {left_df}.join({right_expr}, {join_cond}, how={q(join_type)})"


# ── GroupBy / Agg ─────────────────────────────────────────────

_AGG_FUNCS: dict[str, str] = {
    "sum": "F.sum",
    "avg": "F.avg",
    "mean": "F.mean",
    "count": "F.count",
    "countDistinct": "F.countDistinct",
    "min": "F.min",
    "max": "F.max",
    "first": "F.first",
    "last": "F.last",
    "stddev": "F.stddev",
    "variance": "F.variance",
    "collect_list": "F.collect_list",
    "collect_set": "F.collect_set",
}


def _gen_groupby_agg(block: BlockSpec) -> str:
    p = block.params
    inp = block.input_vars[0] if block.input_vars else "df"
    out = block.output_var
    group_cols = p.get("group_by_cols", [])
    aggs = p.get("aggregations", [])
    gb = (
        f"{inp}.groupBy({', '.join(repr(c) for c in group_cols)})"
        if group_cols
        else f"{inp}.groupBy()"
    )
    agg_exprs: list[str] = []
    for a in aggs:
        fn = _AGG_FUNCS.get(a.get("function", "count"), "F.count")
        col = a.get("column", "*")
        alias = a.get("alias", "") or f"{a.get('function', 'count')}_{col}"
        if a.get("function") == "count" and col == "*":
            agg_exprs.append(f'F.count("*").alias({q(alias)})')
        else:
            agg_exprs.append(f"{fn}({q(col)}).alias({q(alias)})")
    if not agg_exprs:
        return f"{out} = {gb}.agg()"
    return f"{out} = {gb}.agg({', '.join(agg_exprs)})"


# ── Window ────────────────────────────────────────────────────

_WINDOW_TEMPLATES: dict[str, str] = {
    "row_number": "F.row_number()",
    "rank": "F.rank()",
    "dense_rank": "F.dense_rank()",
    "percent_rank": "F.percent_rank()",
    "ntile": "F.ntile({ntile_n})",
    "lead": "F.lead(F.col({lead_lag_col}), {lead_lag_offset})",
    "lag": "F.lag(F.col({lead_lag_col}), {lead_lag_offset})",
    "sum": "F.sum(F.col({agg_col}))",
    "avg": "F.avg(F.col({agg_col}))",
    "min": "F.min(F.col({agg_col}))",
    "max": "F.max(F.col({agg_col}))",
    "count": "F.count(F.col({agg_col}))",
    "first": "F.first(F.col({agg_col}))",
    "last": "F.last(F.col({agg_col}))",
    "cume_dist": "F.cume_dist()",
}


def _frame_boundary(val) -> str:
    s = str(val)
    if s in ("unbounded_preceding", "unbounded"):
        return "Window.unboundedPreceding"
    if s == "unbounded_following":
        return "Window.unboundedFollowing"
    if s in ("current", "0"):
        return "Window.currentRow"
    try:
        return str(int(s))
    except (ValueError, TypeError):
        return "Window.currentRow"


def _gen_window(block: BlockSpec) -> str:
    p = block.params
    inp = block.input_vars[0] if block.input_vars else "df"
    out = block.output_var
    output_col = p.get("output_column", "new_col")
    func_name = p.get("function", "row_number")

    parts = ["Window"]
    part_cols = p.get("partition_by", [])
    if part_cols:
        parts.append(f".partitionBy({', '.join(repr(c) for c in part_cols)})")
    order_cols = p.get("order_by", [])
    if order_cols:
        order_exprs = [
            f"F.col({q(o['column'])}).{o.get('direction', 'asc')}()"
            for o in order_cols
            if o.get("column")
        ]
        if order_exprs:
            parts.append(f".orderBy({', '.join(order_exprs)})")

    frame_type = p.get("frame_type", "unbounded")
    if frame_type in ("rows", "range"):
        start = _frame_boundary(p.get("frame_start", "unbounded_preceding"))
        end = _frame_boundary(p.get("frame_end", "current"))
        method = "rowsBetween" if frame_type == "rows" else "rangeBetween"
        parts.append(f".{method}({start}, {end})")

    template = _WINDOW_TEMPLATES.get(func_name, "F.row_number()")
    func_expr = template.format(
        agg_col=q(p.get("agg_col", "")),
        lead_lag_col=q(p.get("lead_lag_col", "")),
        lead_lag_offset=p.get("lead_lag_offset", 1),
        ntile_n=p.get("ntile_n", 4),
    )
    # Sanitize block_id for use as Python variable name
    safe_id = "".join(c if c.isalnum() or c == "_" else "_" for c in block.block_id[:8])
    win_var = f"w_{safe_id}"
    return f'{win_var} = {"".join(parts)}\n{out} = {inp}.withColumn({q(output_col)}, {func_expr}.over({win_var}))'


# ── String / Date ops ─────────────────────────────────────────

_STRING_TEMPLATES: dict[str, str] = {
    "upper": "F.upper(F.col({col}))",
    "lower": "F.lower(F.col({col}))",
    "trim": "F.trim(F.col({col}))",
    "ltrim": "F.ltrim(F.col({col}))",
    "rtrim": "F.rtrim(F.col({col}))",
    "length": "F.length(F.col({col}))",
    "reverse": "F.reverse(F.col({col}))",
    "substring": "F.substring(F.col({col}), {start}, {length})",
    "split": "F.split(F.col({col}), {delimiter})",
    "concat": "F.concat({concat_cols})",
    "concat_ws": "F.concat_ws({separator}, {concat_cols})",
    "regexp_replace": "F.regexp_replace(F.col({col}), {pattern}, {replacement})",
    "lpad": "F.lpad(F.col({col}), {pad_len}, {pad_char})",
    "rpad": "F.rpad(F.col({col}), {pad_len}, {pad_char})",
    "initcap": "F.initcap(F.col({col}))",
    "translate": "F.translate(F.col({col}), {matching}, {replace})",
}

_DATE_TEMPLATES: dict[str, str] = {
    "current_date": "F.current_date()",
    "current_timestamp": "F.current_timestamp()",
    "to_date": "F.to_date(F.col({col}), {fmt})",
    "to_timestamp": "F.to_timestamp(F.col({col}), {fmt})",
    "date_add": "F.date_add(F.col({col}), {days})",
    "date_sub": "F.date_sub(F.col({col}), {days})",
    "datediff": "F.datediff(F.col({end_col}), F.col({start_col}))",
    "months_between": "F.months_between(F.col({end_col}), F.col({start_col}))",
    "add_months": "F.add_months(F.col({col}), {months})",
    "year": "F.year(F.col({col}))",
    "month": "F.month(F.col({col}))",
    "dayofmonth": "F.dayofmonth(F.col({col}))",
    "dayofweek": "F.dayofweek(F.col({col}))",
    "dayofyear": "F.dayofyear(F.col({col}))",
    "hour": "F.hour(F.col({col}))",
    "minute": "F.minute(F.col({col}))",
    "second": "F.second(F.col({col}))",
    "last_day": "F.last_day(F.col({col}))",
    "trunc": "F.trunc(F.col({col}), {trunc_fmt})",
    "date_format": "F.date_format(F.col({col}), {fmt})",
}


def _format_template(template: str, params: dict) -> str:
    concat_cols_str = ""
    if "concat_cols" in params:
        concat_cols_str = ", ".join(f"F.col({q(c)})" for c in params.get("concat_cols", []))
    return template.format(
        col=q(params.get("col", "")),
        start=params.get("start", 1),
        length=params.get("length", 1),
        delimiter=q(params.get("delimiter", ",")),
        concat_cols=concat_cols_str,
        separator=q(params.get("separator", ",")),
        pattern=q(params.get("pattern", "")),
        replacement=q(params.get("replacement", "")),
        pad_len=params.get("pad_len", 10),
        pad_char=q(params.get("pad_char", " ")),
        matching=q(params.get("matching", "")),
        replace=q(params.get("replace", "")),
        fmt=q(params.get("fmt", "yyyy-MM-dd")),
        days=params.get("days", 1),
        months=params.get("months", 1),
        start_col=q(params.get("start_col", "start")),
        end_col=q(params.get("end_col", "end")),
        trunc_fmt=q(params.get("trunc_fmt", "month")),
    )


def _gen_string_op(block: BlockSpec) -> str:
    p = block.params
    inp = block.input_vars[0] if block.input_vars else "df"
    out = block.output_var
    op = p.get("operation", "upper")
    output_col = p.get("output_column") or p.get("col") or "new_col"
    template = _STRING_TEMPLATES.get(op)
    if not template:
        return f"{out} = {inp}  # Unsupported string op: {op}"
    return f"{out} = {inp}.withColumn({q(output_col)}, {_format_template(template, p)})"


def _gen_date_op(block: BlockSpec) -> str:
    p = block.params
    inp = block.input_vars[0] if block.input_vars else "df"
    out = block.output_var
    op = p.get("operation", "year")
    output_col = p.get("output_column") or p.get("col") or "new_col"
    template = _DATE_TEMPLATES.get(op)
    if not template:
        return f"{out} = {inp}  # Unsupported date op: {op}"
    return f"{out} = {inp}.withColumn({q(output_col)}, {_format_template(template, p)})"


def _gen_custom(block: BlockSpec) -> str:
    code = block.params.get("code", "# No code provided")
    return f"# --- Custom Block: {block.label} ---\n{code}\n# --- End Custom Block ---"


# ═══════════════════════════════════════════════════════════════
#  Dispatch table + master generator
# ═══════════════════════════════════════════════════════════════


def generate(state: PipelineState) -> str:
    """Main entry point. Returns a complete PySpark script string."""
    app_name = state.spark_app_name
    lines: list[str] = [
        '"""',
        f"PySpark Pipeline: {app_name}",
        "Generated by Visual PySpark Code Generator",
        '"""',
        "",
        _collect_imports(state.blocks),
        "",
        "# " + "\u2014" * 40,
        "spark = (",
        "    SparkSession.builder",
        f"    .appName({q(app_name)})",
        "    .getOrCreate()",
        ")",
        "",
        "# " + "\u2014" * 40,
    ]
    for block in state.blocks:
        bt = BLOCKS.get(block.block_type)
        if bt is None or bt.codegen is None:
            lines.append(f"# Unsupported block type: {block.block_type}")
            continue
        lines.append(f"# {block.label}")
        lines.append(bt.codegen(block))
        lines.append("")
    lines += ["# " + "\u2014" * 40, "spark.stop()"]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  Inject generators into the central registry (avoids circular import)
# ═══════════════════════════════════════════════════════════════

BLOCKS["read_csv"].codegen = _gen_read
BLOCKS["read_parquet"].codegen = _gen_read
BLOCKS["read_json"].codegen = _gen_read
BLOCKS["write_csv"].codegen = _gen_write
BLOCKS["write_parquet"].codegen = _gen_write
BLOCKS["select"].codegen = _gen_select
BLOCKS["drop"].codegen = _gen_drop
BLOCKS["rename"].codegen = _gen_rename
BLOCKS["filter"].codegen = _gen_filter
BLOCKS["cast"].codegen = _gen_cast
BLOCKS["when_otherwise"].codegen = _gen_when_otherwise
BLOCKS["join"].codegen = _gen_join
BLOCKS["groupby_agg"].codegen = _gen_groupby_agg
BLOCKS["window"].codegen = _gen_window
BLOCKS["string_op"].codegen = _gen_string_op
BLOCKS["date_op"].codegen = _gen_date_op
BLOCKS["custom"].codegen = _gen_custom
