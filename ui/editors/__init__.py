"""Editor registry — injects editor classes into blocks.py's BLOCKS registry.

Each editor must expose get_params() -> dict.
"""

from __future__ import annotations

from blocks import BLOCKS
from ui.editors.cast import CastEditor
from ui.editors.custom import CustomEditor
from ui.editors.date import DateOpEditor
from ui.editors.drop import DropEditor
from ui.editors.filter import FilterEditor
from ui.editors.groupby import GroupByEditor
from ui.editors.join import JoinEditor
from ui.editors.read import ReadEditor
from ui.editors.rename import RenameEditor
from ui.editors.select import SelectEditor
from ui.editors.string import StringOpEditor
from ui.editors.when_otherwise import WhenOtherwiseEditor
from ui.editors.window import WindowEditor
from ui.editors.write import WriteEditor

# Inject editor classes into the central registry
BLOCKS["read_csv"].editor = ReadEditor
BLOCKS["read_parquet"].editor = ReadEditor
BLOCKS["read_json"].editor = ReadEditor
BLOCKS["write_csv"].editor = WriteEditor
BLOCKS["write_parquet"].editor = WriteEditor
BLOCKS["select"].editor = SelectEditor
BLOCKS["drop"].editor = DropEditor
BLOCKS["rename"].editor = RenameEditor
BLOCKS["filter"].editor = FilterEditor
BLOCKS["cast"].editor = CastEditor
BLOCKS["when_otherwise"].editor = WhenOtherwiseEditor
BLOCKS["join"].editor = JoinEditor
BLOCKS["groupby_agg"].editor = GroupByEditor
BLOCKS["window"].editor = WindowEditor
BLOCKS["string_op"].editor = StringOpEditor
BLOCKS["date_op"].editor = DateOpEditor
BLOCKS["custom"].editor = CustomEditor
