"""
Central block registry — single source of truth for every block type.

FieldSpec drives the generic sentence renderer + collector.
ValidationRule drives the generic validator.
No other file hardcodes block-type-specific logic — they read from here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from helpers import OPERATORS
from schema import SPARK_TYPES

# ═══════════════════════════════════════════════════════════════
#  Import strings (used by codegen)
# ═══════════════════════════════════════════════════════════════

IMP_F = "import pyspark.sql.functions as F"
IMP_T = (
    "from pyspark.sql.types import ("
    "IntegerType, LongType, FloatType, DoubleType, "
    "StringType, BooleanType, DateType, TimestampType, DecimalType)"
)
IMP_W = "from pyspark.sql.window import Window"
IMP_S = "from pyspark.sql import SparkSession"

# Codegen functions are injected by codegen.py after import (avoids circular import)

# ═══════════════════════════════════════════════════════════════
#  Building blocks
# ═══════════════════════════════════════════════════════════════


@dataclass
class FieldSpec:
    """Describes one widget in a sentence row.

    kind       — "label" | "text" | "combo" | "check" | "textarea" | "input_ref" | "stretch"
    param      — key in the block's params dict (used as widget objectName)
    list_key   — if set, value lives in params[list_key][0][sub_key]
    sub_list   — second-level list key (for when/otherwise nested structure)
    sub_key    — key within the list element
    comma_list — param is a list[str], rendered comma-separated
    """

    kind: str
    param: str = ""
    text: str = ""  # display text for labels / checkboxes
    default: Any = ""  # fallback value
    width: int = 0  # fixed pixel width (0 = auto)
    items: list[str] | None = None  # choices for combos
    placeholder: str = ""
    max_height: int = 60  # for textarea
    list_key: str = ""  # outer list name e.g. "conditions"
    sub_list: str = ""  # inner list name e.g. "conditions" (when/otherwise)
    sub_key: str = ""  # key within the element e.g. "column"
    comma_list: bool = False


@dataclass
class ExtraInfo:
    """Conditional text appended to a sentence row (e.g. "+3 more")."""

    list_key: str  # params key to check length
    prefix: str = ""  # e.g. "& " for filters, "+" for mappings
    suffix: str = " more"  # e.g. " more", " keys", " agg"
    threshold: int = 1  # show only when list length > threshold


@dataclass
class ValidationRule:
    """A single validation check for a block type."""

    level: str  # "error" | "warning"
    message: str
    # One of these two:
    param_key: str = ""  # simple check: params[param_key] is empty?
    check_fn: Callable[[dict], bool] | None = None  # custom check


# ═══════════════════════════════════════════════════════════════
#  Generic sentence renderer & collector
# ═══════════════════════════════════════════════════════════════


def get_field_value(params: dict, field: FieldSpec) -> Any:
    """Read a value from params using the field's path spec."""
    if field.list_key:
        lst = params.get(field.list_key, [])
        if not lst:
            return field.default
        if field.sub_list:
            inner = lst[0].get(field.sub_list, [])
            if inner and field.sub_key:
                return inner[0].get(field.sub_key, field.default)
            return field.default
        if field.sub_key:
            return lst[0].get(field.sub_key, field.default)
        return field.default
    if field.comma_list:
        lst = params.get(field.param, [])
        return ", ".join(lst)
    return params.get(field.param, field.default)


def set_field_value(params: dict, field: FieldSpec, value: Any):
    """Write a value into params using the field's path spec."""
    if field.list_key:
        lst = params.setdefault(field.list_key, [])
        if not lst:
            lst.append({})
        if field.sub_list:
            inner = lst[0].setdefault(field.sub_list, [])
            if not inner:
                inner.append({})
            if field.sub_key:
                inner[0][field.sub_key] = value
        elif field.sub_key:
            lst[0][field.sub_key] = value
        return
    if field.comma_list:
        if isinstance(value, str):
            params[field.param] = [c.strip() for c in value.split(",") if c.strip()]
        else:
            params[field.param] = list(value)
        return
    params[field.param] = value


def count_list(params: dict, list_key: str) -> int:
    """Count items in a list-type param for extra-info display."""
    val = params.get(list_key, [])
    return len(val) if isinstance(val, list) else 0


# ═══════════════════════════════════════════════════════════════
#  Block type definitions
# ═══════════════════════════════════════════════════════════════


@dataclass
class BlockTypeDef:
    key: str
    icon: str
    color: str
    label: str
    sentence: list[FieldSpec] = field(default_factory=list)
    extras: list[ExtraInfo] = field(default_factory=list)
    validation: list[ValidationRule] = field(default_factory=list)
    # Codegen
    codegen: Callable | None = None
    imports: set[str] = field(default_factory=set)
    # Wiring
    input_count: int = 1  # 0 = no inputs (reads/custom), 1 = single, 2 = join
    # Editor (set by ui/editors/__init__.py after import)
    editor: type | None = None
    # Help
    help_title: str = ""
    help_what: str = ""
    help_example: str = ""
    help_tip: str = ""


# ── Helper constants for repeated items ───────────────────────

# Operator + Spark-type lists live in helpers.py / schema.py (single source).

_JOIN_TYPES = ["inner", "left", "right", "outer", "left_semi", "left_anti", "cross"]

_AGG_FNS = [
    "sum",
    "avg",
    "mean",
    "count",
    "countDistinct",
    "min",
    "max",
    "first",
    "last",
    "stddev",
    "variance",
    "collect_list",
    "collect_set",
]

_WIN_FNS = [
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "ntile",
    "lead",
    "lag",
    "sum",
    "avg",
    "min",
    "max",
    "count",
    "first",
    "last",
    "cume_dist",
]

_STR_OPS = [
    "upper",
    "lower",
    "trim",
    "ltrim",
    "rtrim",
    "length",
    "reverse",
    "initcap",
    "substring",
    "split",
    "concat",
    "concat_ws",
    "regexp_replace",
    "lpad",
    "rpad",
    "translate",
]

_DATE_OPS = [
    "current_date",
    "current_timestamp",
    "to_date",
    "to_timestamp",
    "date_add",
    "date_sub",
    "datediff",
    "months_between",
    "add_months",
    "year",
    "month",
    "dayofmonth",
    "dayofweek",
    "dayofyear",
    "hour",
    "minute",
    "second",
    "last_day",
    "trunc",
    "date_format",
]


# ═══════════════════════════════════════════════════════════════
#  Registry
# ═══════════════════════════════════════════════════════════════

BLOCKS: dict[str, BlockTypeDef] = {
    # ── Read ──────────────────────────────────────────────
    "read_csv": BlockTypeDef(
        key="read_csv",
        icon="\U0001f4e5",
        color="#2A6EBB",
        label="Read Data",
        sentence=[
            FieldSpec("label", text="READ"),
            FieldSpec(
                "combo",
                param="format",
                items=["csv", "parquet", "json"],
                default="csv",
                width=75,
            ),
            FieldSpec("label", text="FROM"),
            FieldSpec("text", param="path", placeholder="/data/input.csv"),
            FieldSpec("check", param="header", text="Header", default=True),
            FieldSpec("check", param="infer_schema", text="Infer", default=True),
        ],
        validation=[
            ValidationRule("error", "No file path set", param_key="path"),
        ],
        imports={IMP_S},
        input_count=0,
        help_title="\U0001f4e5 Read Data",
        help_what="Loads a file (CSV, Parquet, JSON) into Spark so you can work with it.",
        help_example="Like opening an Excel file, but for datasets too big for Excel.",
        help_tip="Click Browse to find your file. Check 'First row is header' if your file has column names.",
    ),
    "read_parquet": BlockTypeDef(
        key="read_parquet",
        icon="\U0001f4e5",
        color="#2A6EBB",
        label="Read Parquet",
        sentence=[
            FieldSpec("label", text="READ"),
            FieldSpec(
                "combo",
                param="format",
                items=["parquet", "csv", "json"],
                default="parquet",
                width=75,
            ),
            FieldSpec("label", text="FROM"),
            FieldSpec("text", param="path", placeholder="/data/input.parquet"),
        ],
        validation=[
            ValidationRule("error", "No file path set", param_key="path"),
        ],
        imports={IMP_S},
        input_count=0,
        help_title="\U0001f4e5 Read Parquet",
        help_what="Loads a Parquet file into Spark. Parquet is a fast, compressed columnar format.",
        help_example="Read a Parquet file from a data lake for analysis.",
        help_tip="Parquet preserves schema — no need to infer types.",
    ),
    "read_json": BlockTypeDef(
        key="read_json",
        icon="\U0001f4e5",
        color="#2A6EBB",
        label="Read JSON",
        sentence=[
            FieldSpec("label", text="READ"),
            FieldSpec(
                "combo",
                param="format",
                items=["json", "csv", "parquet"],
                default="json",
                width=75,
            ),
            FieldSpec("label", text="FROM"),
            FieldSpec("text", param="path", placeholder="/data/input.json"),
        ],
        validation=[
            ValidationRule("error", "No file path set", param_key="path"),
        ],
        imports={IMP_S},
        input_count=0,
        help_title="\U0001f4e5 Read JSON",
        help_what="Loads a JSON file into Spark. Supports nested structures.",
        help_example="Read API response logs or config files stored as JSON.",
        help_tip="Spark auto-detects schema from JSON, but complex nesting may need flattening later.",
    ),
    "write_csv": BlockTypeDef(
        key="write_csv",
        icon="\U0001f4e4",
        color="#1A7A4A",
        label="Write CSV",
        sentence=[
            FieldSpec("label", text="WRITE"),
            FieldSpec("input_ref", param="__input__"),
            FieldSpec("label", text="TO"),
            FieldSpec("text", param="path", placeholder="/data/output/results"),
            FieldSpec("label", text="AS"),
            FieldSpec(
                "combo",
                param="format",
                items=["csv", "parquet"],
                default="csv",
                width=70,
            ),
            FieldSpec("label", text="MODE"),
            FieldSpec(
                "combo",
                param="mode",
                items=["overwrite", "append", "ignore", "error"],
                default="overwrite",
                width=80,
            ),
        ],
        validation=[
            ValidationRule("error", "No output path", param_key="path"),
        ],
        imports=set(),
        input_count=1,
        help_title="\U0001f4e4 Write CSV",
        help_what="Saves your DataFrame as a CSV file. Human-readable but larger and slower than Parquet.",
        help_example="Export final results for Excel or sharing with non-technical users.",
        help_tip="Use 'overwrite' to replace, 'append' to add rows.",
    ),
    "write_parquet": BlockTypeDef(
        key="write_parquet",
        icon="\U0001f4e4",
        color="#1A7A4A",
        label="Write Parquet",
        sentence=[
            FieldSpec("label", text="WRITE"),
            FieldSpec("input_ref", param="__input__"),
            FieldSpec("label", text="TO"),
            FieldSpec("text", param="path", placeholder="/data/output/results"),
            FieldSpec("label", text="AS"),
            FieldSpec(
                "combo",
                param="format",
                items=["parquet", "csv"],
                default="parquet",
                width=70,
            ),
            FieldSpec("label", text="MODE"),
            FieldSpec(
                "combo",
                param="mode",
                items=["overwrite", "append", "ignore", "error"],
                default="overwrite",
                width=80,
            ),
        ],
        validation=[
            ValidationRule("error", "No output path", param_key="path"),
        ],
        imports=set(),
        input_count=1,
        help_title="\U0001f4e4 Write Parquet",
        help_what="Saves your DataFrame to disk. Parquet is fast and compressed.",
        help_example="After cleaning and transforming, save results for your dashboard or next pipeline.",
        help_tip="'overwrite' replaces existing files. 'append' adds new rows.",
    ),
    "select": BlockTypeDef(
        key="select",
        icon="\U0001f4cb",
        color="#4A6EC0",
        label="Select Columns",
        sentence=[
            FieldSpec("label", text="SELECT"),
            FieldSpec(
                "text", param="columns", placeholder="col1, col2, ...", comma_list=True
            ),
            FieldSpec("label", text="FROM"),
            FieldSpec("input_ref", param="__input__"),
        ],
        extras=[ExtraInfo("columns", prefix="", suffix=" cols", threshold=4)],
        validation=[
            ValidationRule(
                "warning", "No columns selected — output unchanged", param_key="columns"
            ),
        ],
        imports=set(),
        input_count=1,
        help_title="\U0001f4cb Select Columns",
        help_what="Picks which columns to keep. Like hiding columns in a spreadsheet.",
        help_example="Keep only name, email, signup_date from a table with 50 columns.",
        help_tip="Type comma-separated on the card, or one per line in the full editor.",
    ),
    "drop": BlockTypeDef(
        key="drop",
        icon="\U0001f5d1",
        color="#4A6EC0",
        label="Drop Columns",
        sentence=[
            FieldSpec("label", text="DROP"),
            FieldSpec(
                "text", param="columns", placeholder="col1, col2, ...", comma_list=True
            ),
            FieldSpec("label", text="FROM"),
            FieldSpec("input_ref", param="__input__"),
        ],
        extras=[ExtraInfo("columns", prefix="", suffix=" cols", threshold=4)],
        validation=[
            ValidationRule(
                "warning", "No columns to drop — nothing changes", param_key="columns"
            ),
        ],
        imports=set(),
        input_count=1,
        help_title="\U0001f5d1 Drop Columns",
        help_what="Removes columns you don't need. Opposite of Select.",
        help_example="Drop temporary columns or sensitive data like SSN before saving.",
        help_tip="Better to drop what you don't need than select what you do if removing fewer columns.",
    ),
    "rename": BlockTypeDef(
        key="rename",
        icon="\U0001f3f7",
        color="#4A6EC0",
        label="Rename Columns",
        sentence=[
            FieldSpec("label", text="RENAME"),
            FieldSpec(
                "text",
                param="mapping_old",
                placeholder="old name",
                list_key="mappings",
                sub_key="old",
                width=90,
            ),
            FieldSpec("label", text="\u2192"),
            FieldSpec(
                "text",
                param="mapping_new",
                placeholder="new name",
                list_key="mappings",
                sub_key="new",
                width=90,
            ),
            FieldSpec("label", text="IN"),
            FieldSpec("input_ref", param="__input__"),
            FieldSpec("stretch"),
        ],
        extras=[ExtraInfo("mappings", prefix="+", suffix=" more")],
        validation=[
            ValidationRule(
                "warning", "No rename mappings — nothing changes", param_key="mappings"
            ),
        ],
        imports=set(),
        input_count=1,
        help_title="\U0001f3f7 Rename Columns",
        help_what="Changes column names. Old name -> New name.",
        help_example='Rename "cust_id" -> "customer_id" for clarity.',
        help_tip="Consistent naming makes downstream code easier to read.",
    ),
    "filter": BlockTypeDef(
        key="filter",
        icon="\U0001f50d",
        color="#7B3F9E",
        label="Filter / Where",
        sentence=[
            FieldSpec("label", text="WHERE"),
            FieldSpec(
                "text",
                param="filter_col",
                placeholder="column",
                list_key="conditions",
                sub_key="column",
                width=80,
            ),
            FieldSpec(
                "combo",
                param="filter_op",
                items=OPERATORS,
                list_key="conditions",
                sub_key="operator",
                default="==",
                width=80,
            ),
            FieldSpec(
                "text",
                param="filter_val",
                placeholder="value",
                list_key="conditions",
                sub_key="value",
                width=80,
            ),
            FieldSpec("label", text="IN"),
            FieldSpec("input_ref", param="__input__"),
            FieldSpec("stretch"),
        ],
        extras=[ExtraInfo("conditions", prefix="& ", suffix=" more")],
        validation=[
            ValidationRule(
                "warning",
                "No conditions — all rows pass through",
                check_fn=lambda p: (
                    not any(c.get("column") for c in p.get("conditions", []))
                ),
            ),
        ],
        imports={IMP_F},
        input_count=1,
        help_title="\U0001f50d Filter / Where",
        help_what="Keeps only rows that match your conditions. Like a WHERE clause in SQL.",
        help_example='column="age", operator=">=", value="18" -> keeps only adults.',
        help_tip="Use AND/OR to combine conditions. First row is the main condition; extras chain on.",
    ),
    # ── Cast ──────────────────────────────────────────────
    "cast": BlockTypeDef(
        key="cast",
        icon="\U0001f504",
        color="#7B3F9E",
        label="Cast Types",
        sentence=[
            FieldSpec("label", text="CAST"),
            FieldSpec(
                "text",
                param="cast_col",
                placeholder="column",
                list_key="casts",
                sub_key="column",
                width=80,
            ),
            FieldSpec("label", text="\u2192"),
            FieldSpec(
                "combo",
                param="cast_type",
                items=SPARK_TYPES,
                list_key="casts",
                sub_key="target_type",
                default="StringType",
                width=112,
            ),
            FieldSpec("label", text="IN"),
            FieldSpec("input_ref", param="__input__"),
            FieldSpec("stretch"),
        ],
        extras=[ExtraInfo("casts", prefix="+", suffix=" more")],
        validation=[
            ValidationRule(
                "warning",
                "No casts defined — nothing to cast",
                check_fn=lambda p: not any(c.get("column") for c in p.get("casts", [])),
            ),
        ],
        imports={IMP_T, IMP_F},
        input_count=1,
        help_title="\U0001f504 Cast Types",
        help_what="Changes a column's data type. e.g., string -> integer, float -> double.",
        help_example='Cast "price" from StringType to DoubleType so you can do math on it.',
        help_tip="Always check types after reading CSV - Spark often reads numbers as strings.",
    ),
    # ── Join ──────────────────────────────────────────────
    "join": BlockTypeDef(
        key="join",
        icon="\U0001f517",
        color="#C25C00",
        label="Join",
        sentence=[
            FieldSpec("input_ref", param="__left_input__"),
            FieldSpec(
                "combo", param="join_type", items=_JOIN_TYPES, default="inner", width=72
            ),
            FieldSpec("label", text="JOIN"),
            FieldSpec("input_ref", param="__right_input__"),
            FieldSpec("label", text="ON"),
            FieldSpec(
                "text",
                param="join_left",
                placeholder="left key",
                list_key="join_keys",
                sub_key="left",
                width=70,
            ),
            FieldSpec("label", text="="),
            FieldSpec(
                "text",
                param="join_right",
                placeholder="right key",
                list_key="join_keys",
                sub_key="right",
                width=70,
            ),
            FieldSpec("check", param="broadcast_right", text="Broadcast"),
            FieldSpec("stretch"),
        ],
        extras=[ExtraInfo("join_keys", prefix="+", suffix=" keys")],
        validation=[
            ValidationRule(
                "warning",
                "No join keys — try adding keys or use cross join",
                check_fn=lambda p: (
                    not any(
                        k.get("left") and k.get("right") for k in p.get("join_keys", [])
                    )
                    and p.get("join_type") != "cross"
                ),
            ),
        ],
        imports={IMP_F},
        input_count=2,
        help_title="\U0001f517 Join",
        help_what="Combines two DataFrames by matching rows on key columns.",
        help_example="Join 'orders' with 'customers' on customer_id to get customer names with orders.",
        help_tip="Inner = matching rows only. Left = all rows from first table. Check Broadcast for speed.",
    ),
    # ── GroupBy ───────────────────────────────────────────
    "groupby_agg": BlockTypeDef(
        key="groupby_agg",
        icon="\U0001f4ca",
        color="#8B7500",
        label="GroupBy + Agg",
        sentence=[
            FieldSpec(
                "combo",
                param="agg_fn",
                items=_AGG_FNS,
                list_key="aggregations",
                sub_key="function",
                default="sum",
                width=90,
            ),
            FieldSpec("label", text="("),
            FieldSpec(
                "text",
                param="agg_col",
                placeholder="col or *",
                list_key="aggregations",
                sub_key="column",
                width=60,
            ),
            FieldSpec("label", text=")\u2192"),
            FieldSpec(
                "text",
                param="agg_alias",
                placeholder="alias",
                list_key="aggregations",
                sub_key="alias",
                width=70,
            ),
            FieldSpec("label", text="GROUP BY"),
            FieldSpec(
                "text",
                param="group_by_cols",
                placeholder="col1, col2",
                comma_list=True,
                width=100,
            ),
            FieldSpec("label", text="FROM"),
            FieldSpec("input_ref", param="__input__"),
            FieldSpec("stretch"),
        ],
        extras=[ExtraInfo("aggregations", prefix="+", suffix=" agg")],
        validation=[
            ValidationRule(
                "warning",
                "No group-by or aggregations — nothing happens",
                check_fn=lambda p: (
                    not p.get("group_by_cols") and not p.get("aggregations")
                ),
            ),
        ],
        imports={IMP_F},
        input_count=1,
        help_title="\U0001f4ca GroupBy + Aggregate",
        help_what="Groups rows and calculates summaries (sum, avg, count) per group. Like PivotTables.",
        help_example='Group by "department" -> sum of "salary" -> total salary per department.',
        help_tip="Always give aggregations an alias so output columns have clear names.",
    ),
    # ── When / Otherwise ──────────────────────────────────
    "when_otherwise": BlockTypeDef(
        key="when_otherwise",
        icon="\U0001f500",
        color="#7B3F9E",
        label="When / Otherwise",
        sentence=[
            FieldSpec("label", text="WHEN"),
            FieldSpec(
                "text",
                param="when_col",
                placeholder="col",
                width=60,
                list_key="branches",
                sub_list="conditions",
                sub_key="column",
            ),
            FieldSpec(
                "combo",
                param="when_op",
                items=["==", "!=", ">", ">=", "<", "<=", "isNull", "isNotNull"],
                list_key="branches",
                sub_list="conditions",
                sub_key="operator",
                default="==",
                width=65,
            ),
            FieldSpec(
                "text",
                param="when_val",
                placeholder="val",
                width=60,
                list_key="branches",
                sub_list="conditions",
                sub_key="value",
            ),
            FieldSpec("label", text="THEN"),
            FieldSpec(
                "text",
                param="when_result",
                placeholder="result",
                width=60,
                list_key="branches",
                sub_key="result_value",
            ),
            FieldSpec("label", text="ELSE"),
            FieldSpec("text", param="otherwise_value", placeholder="default", width=60),
            FieldSpec("label", text="\u2192"),
            FieldSpec(
                "text",
                param="output_column",
                placeholder="out col",
                default="new_col",
                width=65,
            ),
            FieldSpec("stretch"),
        ],
        extras=[ExtraInfo("branches", prefix="+", suffix="")],
        validation=[
            ValidationRule(
                "warning",
                "No branches defined — output will be empty",
                param_key="branches",
            ),
        ],
        imports={IMP_F},
        input_count=1,
        help_title="\U0001f500 When / Otherwise",
        help_what="Creates a new column based on conditions. Like CASE WHEN in SQL or IF in Excel.",
        help_example='If score > 90 -> "A", elif score > 80 -> "B", else -> "C".',
        help_tip="Each branch has its own conditions + result value. Otherwise is the fallback.",
    ),
    # ── Window ────────────────────────────────────────────
    "window": BlockTypeDef(
        key="window",
        icon="\U0001fa9f",
        color="#8B1A1A",
        label="Window Function",
        sentence=[
            FieldSpec(
                "combo",
                param="function",
                items=_WIN_FNS,
                default="row_number",
                width=85,
            ),
            FieldSpec("label", text="OVER (PARTITION BY"),
            FieldSpec(
                "text",
                param="partition_by",
                placeholder="col1, col2",
                comma_list=True,
                width=100,
            ),
            FieldSpec("label", text="ORDER BY"),
            FieldSpec(
                "text",
                param="order_col",
                placeholder="col",
                width=60,
                list_key="order_by",
                sub_key="column",
            ),
            FieldSpec(
                "combo",
                param="order_dir",
                items=["asc", "desc"],
                list_key="order_by",
                sub_key="direction",
                default="asc",
                width=52,
            ),
            FieldSpec("label", text=")\u2192"),
            FieldSpec(
                "text",
                param="output_column",
                placeholder="out col",
                default="new_col",
                width=65,
            ),
            FieldSpec("stretch"),
        ],
        validation=[
            ValidationRule(
                "warning", "No output column name set", param_key="output_column"
            ),
        ],
        imports={IMP_F, IMP_W},
        input_count=1,
        help_title="\U0001fa9f Window Function",
        help_what="Calculates values across a sliding window of rows. Like GroupBy but keeps all rows.",
        help_example="Rank employees by salary within each department. Running total over time.",
        help_tip="Partition By = groups. Order By = ranking order. Frame = how many surrounding rows to include.",
    ),
    # ── String Op ─────────────────────────────────────────
    "string_op": BlockTypeDef(
        key="string_op",
        icon="Aa",
        color="#2D7A6E",
        label="String Op",
        sentence=[
            FieldSpec(
                "combo", param="operation", items=_STR_OPS, default="upper", width=85
            ),
            FieldSpec("label", text="("),
            FieldSpec("text", param="col", placeholder="column", width=70),
            FieldSpec("label", text=")\u2192"),
            FieldSpec("text", param="output_column", placeholder="out col", width=70),
            FieldSpec("stretch"),
        ],
        validation=[
            ValidationRule("warning", "No input column set", param_key="col"),
        ],
        imports={IMP_F},
        input_count=1,
        help_title="Aa String Op",
        help_what="Transforms text columns: uppercase, lowercase, trim, split, concat, etc.",
        help_example='upper("name") -> "JOHN DOE". concat(first_name, last_name) -> "JohnDoe".',
        help_tip="Use trim() after reading CSVs to remove stray spaces.",
    ),
    # ── Date Op ───────────────────────────────────────────
    "date_op": BlockTypeDef(
        key="date_op",
        icon="\U0001f4c5",
        color="#2D7A6E",
        label="Date / Time Op",
        sentence=[
            FieldSpec(
                "combo", param="operation", items=_DATE_OPS, default="year", width=100
            ),
            FieldSpec("label", text="("),
            FieldSpec("text", param="col", placeholder="column", width=70),
            FieldSpec("label", text=")\u2192"),
            FieldSpec("text", param="output_column", placeholder="out col", width=70),
            FieldSpec("stretch"),
        ],
        validation=[
            ValidationRule(
                "warning",
                "No input column set",
                check_fn=lambda p: (
                    not p.get("col", "").strip()
                    and p.get("operation") not in ("current_date", "current_timestamp")
                ),
            ),
        ],
        imports={IMP_F},
        input_count=1,
        help_title="\U0001f4c5 Date / Time Op",
        help_what="Extracts or transforms date/time values: year, month, day, date_add, etc.",
        help_example='year("order_date") -> 2024. date_add("order_date", 7) -> one week later.',
        help_tip="current_date() and current_timestamp() don't need an input column.",
    ),
    # ── Custom ────────────────────────────────────────────
    "custom": BlockTypeDef(
        key="custom",
        icon="\U0001f4bb",
        color="#555555",
        label="Custom Code",
        sentence=[
            FieldSpec("label", text="CUSTOM CODE:"),
            FieldSpec(
                "textarea",
                param="code",
                placeholder="# Your PySpark code here...",
                max_height=50,
            ),
        ],
        validation=[
            ValidationRule(
                "warning", "No custom code — block does nothing", param_key="code"
            ),
        ],
        imports=set(),
        input_count=0,
        help_title="\U0001f4bb Custom Code",
        help_what="Paste any PySpark code. It's inserted verbatim into the generated script.",
        help_example="Use this for operations not covered by other blocks, or to add comments/print statements.",
        help_tip="Reference previous DataFrames by their variable names (shown in the blue labels on each card).",
    ),
}


# ═══════════════════════════════════════════════════════════════
#  Palette entries (label → key mapping for the left panel)
# ═══════════════════════════════════════════════════════════════

PALETTE: list[tuple[str, str]] = [
    ("\U0001f4e5  Read Data", "read_csv"),
    ("\U0001f4e4  Write Data", "write_parquet"),
    ("\U0001f4cb  Select Columns", "select"),
    ("\U0001f5d1   Drop Columns", "drop"),
    ("\U0001f3f7   Rename Columns", "rename"),
    ("\U0001f50d  Filter / Where", "filter"),
    ("\U0001f504  Cast Types", "cast"),
    ("\U0001f500  When / Otherwise", "when_otherwise"),
    ("\U0001f517  Join", "join"),
    ("\U0001f4ca  GroupBy + Agg", "groupby_agg"),
    ("\U0001fa9f  Window Function", "window"),
    ("Aa  String Op", "string_op"),
    ("\U0001f4c5  Date / Time Op", "date_op"),
    ("\U0001f4bb  Custom Code", "custom"),
]
