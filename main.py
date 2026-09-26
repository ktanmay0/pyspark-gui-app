"""
Entry point — python main.py
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from theme import apply
from ui.window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply(app, "dark")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
