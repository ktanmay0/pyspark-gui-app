"""Toolbar — reusable builder, no dependency on MainWindow."""

from __future__ import annotations

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QSizePolicy, QToolBar, QWidget


def build_toolbar(
    *,
    on_new: callable,
    on_open: callable,
    on_save: callable,
    on_schema: callable,
    on_copy: callable,
    on_export: callable,
    on_theme: callable,
) -> QToolBar:
    tb = QToolBar("Main")
    tb.setMovable(False)
    tb.setIconSize(QSize(18, 18))

    tb.addAction("New", on_new)
    tb.addAction("Open…", on_open)
    tb.addAction("Save…", on_save)
    tb.addSeparator()
    tb.addAction("Schema Editor…", on_schema)
    tb.addSeparator()

    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    tb.addWidget(spacer)

    title = QLabel(
        "<b style='font-size:14px; color:#89B4FA'>⚡ PySpark Pipeline Builder</b>"
    )
    title.setStyleSheet("background: transparent;")
    tb.addWidget(title)

    spacer2 = QWidget()
    spacer2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    tb.addWidget(spacer2)

    tb.addAction("Copy Code", on_copy)
    tb.addAction("Export .py", on_export)
    tb.addSeparator()

    theme_action = QAction("🌓 Toggle Theme", tb)
    theme_action.triggered.connect(on_theme)
    tb.addAction(theme_action)

    return tb
