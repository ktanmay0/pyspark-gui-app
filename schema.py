"""
Schema Manager — table schemas (column names + types) and CSV import.

Pure data classes only — no UI dependencies live here.  The autocomplete
helper moved to ``ui.widgets`` so the data layer stays Qt-free.
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass, field

# ── Spark type catalogue ──────────────────────────────────────
SPARK_TYPES = [
    "IntegerType",
    "LongType",
    "FloatType",
    "DoubleType",
    "StringType",
    "BooleanType",
    "DateType",
    "TimestampType",
    "DecimalType",
    "BinaryType",
    "ArrayType",
    "MapType",
    "StructType",
]

# ── Type-inference patterns ───────────────────────────────────
_DATE_PATS = [
    re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    re.compile(r"^\d{2}/\d{2}/\d{4}$"),
    re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$"),
    re.compile(r"^\d{4}/\d{2}/\d{2}$"),
]
_TS_PATS = [
    re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}"),
    re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}"),
]
_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.?\d*([eE][+-]?\d+)?$")
_BOOLS = {"true", "false", "0", "1", "yes", "no"}


def _is_int(s: str) -> bool:
    return bool(_INT_RE.match(s.strip()))


def _is_float(s: str) -> bool:
    return bool(_FLOAT_RE.match(s.strip()))


def _is_date(s: str) -> bool:
    return any(p.match(s.strip()) for p in _DATE_PATS)


def _is_ts(s: str) -> bool:
    return any(p.match(s.strip()) for p in _TS_PATS)


def _is_bool(s: str) -> bool:
    return s.strip().lower() in _BOOLS


def infer_column_type(values: list[str]) -> tuple[str, bool]:
    """(Spark-type-string, nullable) from sample values."""
    non_empty = [v for v in values if v.strip()]
    nullable = len(non_empty) < len(values)
    if not non_empty:
        return "StringType", True

    if all(_is_int(v) for v in non_empty):
        try:
            return (
                ("LongType", nullable)
                if max(abs(int(v)) for v in non_empty) >= 2_147_483_647
                else ("IntegerType", nullable)
            )
        except ValueError:
            return "LongType", nullable
    if all(_is_float(v) for v in non_empty):
        return "DoubleType", nullable
    if all(_is_bool(v) for v in non_empty):
        return "BooleanType", nullable
    if all(_is_date(v) for v in non_empty):
        return "DateType", nullable
    if all(_is_ts(v) for v in non_empty):
        return "TimestampType", nullable
    return "StringType", nullable


def infer_schema_from_csv(csv_path: str, sample_rows: int = 100):
    """Read a CSV file → TableSchema (or None on error)."""
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header is None:
                return None
            col_names = [h.strip() for h in header]
            samples: list[list[str]] = [[] for _ in col_names]
            for row_num, row in enumerate(reader):
                if row_num >= sample_rows:
                    break
                for i, val in enumerate(row):
                    if i < len(col_names):
                        samples[i].append(val.strip())

            columns = []
            for i, name in enumerate(col_names):
                dtype, nullable = infer_column_type(samples[i])
                columns.append(ColumnDef(name=name, data_type=dtype, nullable=nullable))
            return TableSchema(
                table_name=os.path.splitext(os.path.basename(csv_path))[0],
                columns=columns,
            )
    except (OSError, csv.Error) as exc:
        # Surface real I/O / parse errors instead of swallowing them silently.
        print(f"[schema] CSV import failed for {csv_path!r}: {exc}")
        return None
    except Exception as exc:  # pragma: no cover - unexpected, but don't crash UI
        print(f"[schema] Unexpected error importing {csv_path!r}: {exc}")
        return None


# ═══════════════════════════════════════════════════════════════
#  Data classes
# ═══════════════════════════════════════════════════════════════


@dataclass
class ColumnDef:
    name: str = ""
    data_type: str = "StringType"
    nullable: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "nullable": self.nullable,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ColumnDef:
        return cls(
            d.get("name", ""), d.get("data_type", "StringType"), d.get("nullable", True)
        )


@dataclass
class TableSchema:
    table_name: str = ""
    alias: str = ""
    columns: list[ColumnDef] = field(default_factory=list)

    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def to_dict(self) -> dict:
        return {
            "table_name": self.table_name,
            "alias": self.alias,
            "columns": [c.to_dict() for c in self.columns],
        }

    @classmethod
    def from_dict(cls, d: dict) -> TableSchema:
        return cls(
            table_name=d.get("table_name", ""),
            alias=d.get("alias", ""),
            columns=[ColumnDef.from_dict(c) for c in d.get("columns", [])],
        )


@dataclass
class SchemaRegistry:
    tables: list[TableSchema] = field(default_factory=list)

    def add_table(self, table: TableSchema) -> None:
        self.tables.append(table)

    def remove_table(self, index: int) -> None:
        if 0 <= index < len(self.tables):
            self.tables.pop(index)

    def get_table(self, name: str) -> TableSchema | None:
        for t in self.tables:
            if t.table_name == name or t.alias == name:
                return t
        return None

    def all_column_names(self) -> list[str]:
        seen: set[str] = set()
        names: list[str] = []
        for t in self.tables:
            for c in t.columns:
                if c.name not in seen:
                    seen.add(c.name)
                    names.append(c.name)
        return names

    def to_dict(self) -> dict:
        return {"tables": [t.to_dict() for t in self.tables]}

    @classmethod
    def from_dict(cls, d: dict) -> SchemaRegistry:
        return cls(tables=[TableSchema.from_dict(t) for t in d.get("tables", [])])
