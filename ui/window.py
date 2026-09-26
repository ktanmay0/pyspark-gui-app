"""
MainWindow — clean splitter layout with collapsible palette and preview panels.
"""

from __future__ import annotations

import os

from PyQt6.QtCore import QEvent, QSettings, Qt
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import theme
from pipeline import PipelineController
from theme import THEME_NAMES, apply, current
from ui.canvas import Canvas
from ui.dialog import BlockEditorDialog
from ui.help_panel import HelpPanel
from ui.palette import Palette
from ui.preview import Preview


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._ctrl = PipelineController(self)
        self._settings = QSettings("PySparkCodeGen", "PipelineBuilder")

        self.setWindowTitle("PySpark Builder")
        self._restore_state()
        self.setMinimumSize(480, 400)

        self._build_ui()
        self._bind_shortcuts()
        self._connect_signals()
        self._ctrl.pipeline_changed.emit()
        self._update_title()

        theme.on_theme_change(self._on_theme_changed)
        self._apply_theme()

        last_file = self._settings.value("last_file", "")
        if last_file:
            if os.path.exists(last_file):
                self._ctrl.load_pipeline(last_file)

    def _restore_state(self):
        geo = self._settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(1300, 800)
        state = self._settings.value("window_state")
        if state:
            self.restoreState(state)
        # Restore the saved theme (default dark for first run).
        saved_theme = self._settings.value("theme", "dark")
        if saved_theme and saved_theme in THEME_NAMES:
            apply(QApplication.instance(), saved_theme)

    def _save_state(self):
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("window_state", self.saveState())
        self._settings.setValue("theme", current())

    def closeEvent(self, event):
        if self._ctrl.is_dirty:
            r = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if r == QMessageBox.StandardButton.Save:
                path, _ = QFileDialog.getSaveFileName(self, "Save", "", "JSON (*.json)")
                if path:
                    self._ctrl.save_pipeline(path)
                    self._settings.setValue("last_file", path)
                else:
                    event.ignore()
                    return
            elif r == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        self._save_state()
        super().closeEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange and self.isActiveWindow():
            if self._ctrl.check_file_changed():
                r = QMessageBox.question(
                    self,
                    "File Changed",
                    "The file was modified externally. Reload?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if r == QMessageBox.StandardButton.Yes:
                    self._ctrl.reload_current()
        super().changeEvent(event)

    # ── Build UI ──────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        self._header = QWidget()
        self._header.setFixedHeight(46)
        hlay = QHBoxLayout(self._header)
        hlay.setContentsMargins(12, 0, 10, 0)
        hlay.setSpacing(8)

        self._title = QLabel("\u26a1")
        hlay.addWidget(self._title)

        self._app_name_edit = QLineEdit(self._ctrl.state.spark_app_name)
        self._app_name_edit.setPlaceholderText("Pipeline name\u2026")
        self._app_name_edit.setFixedWidth(200)
        self._app_name_edit.editingFinished.connect(self._on_app_name_changed)
        hlay.addWidget(self._app_name_edit)
        hlay.addStretch()

        self._palette_btn = QPushButton("\u25a0 Blocks")
        self._palette_btn.setCheckable(True)
        self._palette_btn.setChecked(True)
        self._palette_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._palette_btn.toggled.connect(self._toggle_palette)
        hlay.addWidget(self._palette_btn)

        self._add_btn = QPushButton("+ Add Block")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._on_add_block_dialog)
        hlay.addWidget(self._add_btn)

        self._code_btn = QPushButton("</> Code")
        self._code_btn.setCheckable(True)
        self._code_btn.setChecked(True)
        self._code_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._code_btn.toggled.connect(self._toggle_preview)
        hlay.addWidget(self._code_btn)

        self._more_btn = QPushButton("\u22ef")
        self._more_btn.setFixedSize(34, 30)
        self._more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        more_menu = QMenu(self)
        a = QAction("New", self)
        a.setShortcut(QKeySequence.StandardKey.New)
        a.triggered.connect(self._on_new)
        more_menu.addAction(a)
        a = QAction("Open\u2026", self)
        a.setShortcut(QKeySequence.StandardKey.Open)
        a.triggered.connect(self._on_open)
        more_menu.addAction(a)
        a = QAction("Save\u2026", self)
        a.setShortcut(QKeySequence.StandardKey.Save)
        a.triggered.connect(self._on_save)
        more_menu.addAction(a)
        more_menu.addSeparator()
        a = QAction("Copy Code", self)
        a.setShortcut("Ctrl+Shift+C")
        a.triggered.connect(self._on_copy)
        more_menu.addAction(a)
        a = QAction("Export .py\u2026", self)
        a.setShortcut("Ctrl+Shift+S")
        a.triggered.connect(self._on_export)
        more_menu.addAction(a)
        more_menu.addSeparator()
        tmpl = more_menu.addMenu("Templates")
        tmpl.addAction(
            "Quick CSV Analysis", lambda: self._load_template("quick_csv_analysis")
        )
        tmpl.addAction("Data Cleaning", lambda: self._load_template("data_cleaning"))
        tmpl.addAction("Join & Enrich", lambda: self._load_template("join_enrich"))
        more_menu.addSeparator()
        more_menu.addAction("Sort Pipeline", self._ctrl.sort_pipeline)
        more_menu.addAction("Explain Pipeline\u2026", self._on_explain)
        more_menu.addAction("Schema Editor\u2026", self._on_schema)
        more_menu.addAction("Toggle Theme", self._on_toggle_theme)
        a = QAction("Shortcuts", self)
        a.setShortcut("F1")
        a.triggered.connect(self._show_cheatsheet)
        more_menu.addAction(a)
        self._more_btn.setMenu(more_menu)
        hlay.addWidget(self._more_btn)
        root.addWidget(self._header)

        # ── Splitter ──
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._palette = Palette(on_block_clicked=self._on_add_block)
        self._canvas = Canvas(
            on_add=self._on_add_block_dialog, on_template=self._load_template
        )
        self._preview = Preview()
        self._help = HelpPanel()
        self._help.hide()
        self._splitter.addWidget(self._palette)
        self._splitter.addWidget(self._canvas)
        self._splitter.addWidget(self._preview)
        self._splitter.addWidget(self._help)
        self._splitter.setSizes([170, 500, 280, 0])
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 3)
        self._splitter.setStretchFactor(2, 1)
        root.addWidget(self._splitter)

    def _toggle_palette(self, show: bool):
        self._palette.setVisible(show)

    def _toggle_preview(self, show: bool):
        self._preview.setVisible(show)

    # ── Theming ───────────────────────────────────────────

    def _apply_theme(self) -> None:
        t = theme.tokens()
        self._header.setStyleSheet(
            f"QWidget {{ background: {t['bg_elevated']};"
            f" border-bottom: 1px solid {t['border']}; }}"
        )
        self._title.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {t['accent']};"
            f" background: transparent; padding-right: 2px;"
        )
        self._app_name_edit.setStyleSheet(
            f"QLineEdit {{ background: transparent; color: {t['text']};"
            f" border: 1px solid transparent; border-radius: 4px;"
            f" padding: 4px 8px; font-size: 13px; font-weight: 600; }}"
            f"QLineEdit:focus {{ border: 1px solid {t['border_strong']};"
            f" background: {t['bg_base']}; }}"
        )
        btn = (
            f"QPushButton {{ background: {t['bg_hover']}; color: {t['text_dim']};"
            f" border: 1px solid {t['border_subtle']}; border-radius: 6px;"
            f" padding: 6px 12px; font-size: 12px; font-weight: 500; }}"
            f"QPushButton:hover {{ background: {t['bg_hover_strong']};"
            f" color: {t['text']}; }}"
            f"QPushButton:checked {{ background: {t['accent_dim']};"
            f" color: {t['accent']}; border-color: {t['accent']}; }}"
            f"QPushButton:pressed {{ background: {t['bg_pressed']}; }}"
        )
        for b in (self._palette_btn, self._code_btn, self._more_btn):
            b.setStyleSheet(btn)
        self._add_btn.setStyleSheet(
            f"QPushButton {{ background: {t['accent']}; color: {t['accent_text']};"
            f" border: none; border-radius: 6px; padding: 6px 14px;"
            f" font-size: 12px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {t['accent_hover']}; }}"
            f"QPushButton:pressed {{ background: {t['accent']}; }}"
        )

    def _on_theme_changed(self) -> None:
        """Restyle chrome + rebuild cards so they pick up new tokens."""
        self._apply_theme()
        self._on_pipeline_changed()

    # ── Title + dirty indicator ───────────────────────────

    def _update_title(self, msg: str = "") -> None:
        """Build the window title: 'PySpark Builder — AppName [*] [— status]'."""
        name = self._ctrl.state.spark_app_name
        dirty = " *" if self._ctrl.is_dirty else ""
        suffix = f" \u2014 {msg}" if msg else ""
        self.setWindowTitle(f"PySpark Builder \u2014 {name}{dirty}{suffix}")

    def _on_app_name_changed(self) -> None:
        name = self._app_name_edit.text().strip()
        if name and name != self._ctrl.state.spark_app_name:
            self._ctrl.set_app_name(name)
            self._update_title()
        else:
            self._app_name_edit.setText(self._ctrl.state.spark_app_name)

    # ── Explain pipeline ──────────────────────────────────

    def _on_explain(self):
        from ui.explain_dialog import ExplainDialog

        dlg = ExplainDialog(self._ctrl.state, parent=self)
        dlg.exec()

    # ── Shortcuts ─────────────────────────────────────────

    def _bind_shortcuts(self):
        QShortcut(QKeySequence.StandardKey.New, self, self._on_new)
        QShortcut(QKeySequence.StandardKey.Open, self, self._on_open)
        QShortcut(QKeySequence.StandardKey.Save, self, self._on_save)
        QShortcut("Ctrl+Shift+S", self, self._on_export)
        QShortcut(QKeySequence.StandardKey.Undo, self, self._ctrl.undo)
        QShortcut(QKeySequence.StandardKey.Redo, self, self._ctrl.redo)
        QShortcut("Ctrl+E", self, self._edit_last)
        QShortcut(QKeySequence.StandardKey.Delete, self, self._delete_last)
        QShortcut("Ctrl+Shift+C", self, self._on_copy)
        QShortcut(QKeySequence("F1"), self, self._show_cheatsheet)
        QShortcut("Ctrl+B", self, self._toggle_palette_shortcut)
        QShortcut("Ctrl+I", self, self._on_explain)

    def _toggle_palette_shortcut(self):
        self._palette_btn.toggle()

    # ── Signals ───────────────────────────────────────────

    def _connect_signals(self):
        self._ctrl.pipeline_changed.connect(self._on_pipeline_changed)
        self._ctrl.code_changed.connect(self._preview.set_code)
        self._ctrl.status.connect(lambda msg: self._update_title(msg))
        self._ctrl.dirty_changed.connect(lambda _: self._update_title())
        self._ctrl.code_changed.emit(self._ctrl.current_code())

    def _on_pipeline_changed(self):
        # Sync the app name field if the state changed externally (load/undo).
        if self._app_name_edit.text() != self._ctrl.state.spark_app_name:
            self._app_name_edit.setText(self._ctrl.state.spark_app_name)
        self._canvas.rebuild(
            self._ctrl.state.blocks,
            on_edit=self._on_edit,
            on_delete=self._on_delete,
            on_duplicate=self._on_duplicate,
            on_move_up=lambda bid: self._ctrl.move_block(bid, -1),
            on_move_down=lambda bid: self._ctrl.move_block(bid, 1),
            on_label_changed=self._ctrl.rename_block,
            on_var_changed=lambda bid, v: self._ctrl.rename_var(bid, v),
            on_card_clicked=lambda bid, bt: (
                self._help.show_for_block(bt),
                self._help.show(),
                self._help.raise_(),
            ),
            on_params_changed=lambda bid, p: self._ctrl.update_params_quiet(bid, p),
            on_reorder=lambda bid, tgt: self._ctrl.reorder_block(bid, tgt),
        )

    def _on_duplicate(self, block_id: str):
        self._ctrl.duplicate_block(block_id)

    # ── Block actions ─────────────────────────────────────

    def _on_add_block(self, btype: str):
        self._ctrl.add_block(btype, _default_label(btype, len(self._ctrl.state.blocks)))

    def _on_add_block_dialog(self):
        from PyQt6.QtWidgets import QInputDialog

        from ui.palette import BLOCK_TYPES

        labels = [
            lbl.split("  ", 1)[1] if "  " in lbl else lbl for lbl, _ in BLOCK_TYPES
        ]
        label, ok = QInputDialog.getItem(self, "Add Block", "Type:", labels, 0, False)
        if ok:
            for lbl, bt in BLOCK_TYPES:
                if (
                    lbl.endswith(label)
                    or (lbl.split("  ", 1)[1] if "  " in lbl else lbl) == label
                ):
                    self._on_add_block(bt)
                    break

    def _on_edit(self, bid):
        b = self._ctrl.state.get_block(bid)
        if b is None:
            return
        dlg = BlockEditorDialog(b, schemas=self._ctrl.state.schemas, parent=self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self._ctrl.update_block(bid, dlg.get_block().params)

    def _on_delete(self, bid):
        self._ctrl.remove_block(bid)

    def _edit_last(self):
        if self._ctrl.state.blocks:
            self._on_edit(self._ctrl.state.blocks[-1].block_id)

    def _delete_last(self):
        if self._ctrl.state.blocks:
            self._ctrl.remove_block(self._ctrl.state.blocks[-1].block_id)

    # ── File actions ──────────────────────────────────────

    def _on_new(self):
        if self._ctrl.state.blocks:
            r = QMessageBox.question(
                self,
                "New",
                "Discard current pipeline?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if r != QMessageBox.StandardButton.Yes:
                return
        self._ctrl.new_pipeline()

    def _on_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open", "", "JSON (*.json)")
        if path:
            self._ctrl.load_pipeline(path)
            self._settings.setValue("last_file", path)

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save", "", "JSON (*.json)")
        if path:
            self._ctrl.save_pipeline(path)
            self._settings.setValue("last_file", path)

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export", "", "Python (*.py)")
        if path:
            self._ctrl.export_script(path)

    def _on_copy(self):
        QApplication.clipboard().setText(self._ctrl.copy_code())

    def _on_schema(self):
        from ui.editors.schema_editor import SchemaEditorDialog

        dlg = SchemaEditorDialog(self._ctrl.state.schemas, parent=self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self._ctrl.update_schemas(dlg.get_registry())

    def _on_toggle_theme(self):
        nxt = THEME_NAMES[1] if current() == THEME_NAMES[0] else THEME_NAMES[0]
        apply(QApplication.instance(), nxt)

    def _show_cheatsheet(self):
        from ui.cheatsheet import CheatsheetDialog

        CheatsheetDialog(self).exec()

    def _load_template(self, name: str):
        if self._ctrl.state.blocks:
            r = QMessageBox.question(
                self,
                "Template",
                "Replace current pipeline?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if r != QMessageBox.StandardButton.Yes:
                return
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "templates",
            f"{name}.json",
        )
        path = os.path.normpath(path)
        if os.path.exists(path):
            self._ctrl.load_pipeline(path)


def _default_label(btype: str, n: int) -> str:
    from ui.palette import BLOCK_TYPES

    name = next(
        (
            lbl.split("  ", 1)[1] if "  " in lbl else lbl
            for lbl, bt in BLOCK_TYPES
            if bt == btype
        ),
        btype,
    )
    return f"{name} {n + 1}"
