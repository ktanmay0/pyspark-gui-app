"""
Theme manager — dark (Catppuccin Mocha) and light (warm parchment).

Single source of truth for every color the UI uses.  Widgets read named
tokens via ``theme.tokens()`` instead of hardcoding hex values, so the
whole app restyles consistently when the theme switches.

    apply(app, "dark"|"light")   — set palette + stylesheet + notify
    tokens()                     — current theme's color dict
    on_theme_change(callback)    — register a restyle callback
    current()                    — active theme name
"""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtGui import QColor, QPalette

THEME_NAMES = ("dark", "light")
_current = "dark"
_listeners: list[Callable[[], None]] = []

# ═══════════════════════════════════════════════════════════════
#  Color tokens
# ═══════════════════════════════════════════════════════════════

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        # surfaces
        "bg": "#1E1E2E",
        "bg_elevated": "#11111B",
        "bg_base": "#181825",
        "bg_surface": "#313244",
        "bg_hover": "rgba(255,255,255,0.08)",
        "bg_hover_strong": "rgba(255,255,255,0.14)",
        "bg_pressed": "rgba(255,255,255,0.04)",
        # lines
        "border": "#45475A",
        "border_subtle": "rgba(255,255,255,0.08)",
        "border_strong": "#89B4FA",
        # text
        "text": "#CDD6F4",
        "text_dim": "#BAC2DE",
        "text_muted": "#6C7086",
        "text_faint": "#585B70",
        # accents
        "accent": "#89B4FA",
        "accent_hover": "#A6C8FF",
        "accent_text": "#1E1E2E",
        "accent_dim": "rgba(137,180,250,0.15)",
        # status
        "danger": "#F38BA8",
        "danger_bg": "rgba(243,139,168,0.18)",
        "warning": "#FAB387",
        "success": "#A6E3A1",
        # card-internal (cards keep white text on colored bg in both themes)
        "card_overlay": "rgba(0,0,0,0.25)",
        "card_overlay_focus": "rgba(255,255,255,0.55)",
        "card_border": "rgba(255,255,255,0.12)",
        "card_border_hover": "rgba(255,255,255,0.40)",
        "card_text": "#FFFFFF",
        "card_label": "rgba(255,255,255,0.60)",
        "card_input_ref": "#B4D0FB",
        "card_btn_bg": "rgba(255,255,255,0.10)",
        "card_btn_hover": "rgba(255,255,255,0.30)",
        "card_del_bg": "rgba(255,80,80,0.20)",
        "card_del_hover": "rgba(255,80,80,0.50)",
        "card_del_text": "#FF8888",
        "arrow": "#585B70",
        # syntax highlight
        "kw": "#CF8E6D",
        "str": "#A6E3A1",
        "cmt": "#6C7086",
        "num": "#2AACB8",
    },
    "light": {
        "bg": "#FBF6F0",
        "bg_elevated": "#F0E6D8",
        "bg_base": "#FFFBF7",
        "bg_surface": "#E6D5C3",
        "bg_hover": "rgba(62,39,35,0.06)",
        "bg_hover_strong": "rgba(62,39,35,0.12)",
        "bg_pressed": "rgba(62,39,35,0.03)",
        "border": "#C4B5A5",
        "border_subtle": "rgba(62,39,35,0.12)",
        "border_strong": "#A67B5B",
        "text": "#3E2723",
        "text_dim": "#5D4A3C",
        "text_muted": "#8B7355",
        "text_faint": "#B0A090",
        "accent": "#A67B5B",
        "accent_hover": "#C28E6A",
        "accent_text": "#FFFFFF",
        "accent_dim": "rgba(166,123,91,0.15)",
        "danger": "#C0392B",
        "danger_bg": "rgba(192,57,43,0.12)",
        "warning": "#B9770E",
        "success": "#2E7D52",
        # cards keep white text on colored bg
        "card_overlay": "rgba(0,0,0,0.22)",
        "card_overlay_focus": "rgba(0,0,0,0.55)",
        "card_border": "rgba(0,0,0,0.15)",
        "card_border_hover": "rgba(0,0,0,0.35)",
        "card_text": "#FFFFFF",
        "card_label": "rgba(255,255,255,0.75)",
        "card_input_ref": "#DCE9F7",
        "card_btn_bg": "rgba(255,255,255,0.22)",
        "card_btn_hover": "rgba(255,255,255,0.40)",
        "card_del_bg": "rgba(255,255,255,0.25)",
        "card_del_hover": "rgba(255,255,255,0.45)",
        "card_del_text": "#FFD6D6",
        "arrow": "#B0A090",
        "kw": "#9C6B43",
        "str": "#2E7D52",
        "cmt": "#A89A86",
        "num": "#0E7C86",
    },
}


def tokens() -> dict[str, str]:
    """Return the active theme's color tokens."""
    return THEMES[_current]


def current() -> str:
    return _current


def on_theme_change(callback: Callable[[], None]) -> None:
    """Register a callback invoked whenever the theme changes."""
    _listeners.append(callback)


# ═══════════════════════════════════════════════════════════════
#  Palettes
# ═══════════════════════════════════════════════════════════════


def _dark_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor("#1E1E2E"))
    p.setColor(QPalette.ColorRole.WindowText, QColor("#CDD6F4"))
    p.setColor(QPalette.ColorRole.Base, QColor("#181825"))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#1E1E2E"))
    p.setColor(QPalette.ColorRole.Text, QColor("#CDD6F4"))
    p.setColor(QPalette.ColorRole.Button, QColor("#313244"))
    p.setColor(QPalette.ColorRole.ButtonText, QColor("#CDD6F4"))
    p.setColor(QPalette.ColorRole.BrightText, QColor("#F38BA8"))
    p.setColor(QPalette.ColorRole.Highlight, QColor("#89B4FA"))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#1E1E2E"))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor("#6C7086"))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor("#313244"))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor("#CDD6F4"))
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        p.setColor(QPalette.ColorGroup.Disabled, role, QColor("#585B70"))
    return p


def _light_palette() -> QPalette:
    p = QPalette()
    db = QColor("#3E2723")
    p.setColor(QPalette.ColorRole.Window, QColor("#FBF6F0"))
    p.setColor(QPalette.ColorRole.WindowText, db)
    p.setColor(QPalette.ColorRole.Base, QColor("#FFFBF7"))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#F5EDE3"))
    p.setColor(QPalette.ColorRole.Text, db)
    p.setColor(QPalette.ColorRole.Button, QColor("#E6D5C3"))
    p.setColor(QPalette.ColorRole.ButtonText, db)
    p.setColor(QPalette.ColorRole.BrightText, QColor("#C0392B"))
    p.setColor(QPalette.ColorRole.Highlight, QColor("#A67B5B"))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor("#A09080"))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FBF6F0"))
    p.setColor(QPalette.ColorRole.ToolTipText, db)
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        p.setColor(QPalette.ColorGroup.Disabled, role, QColor("#B0A090"))
    return p


_PALETTES = {"dark": _dark_palette, "light": _light_palette}

# ═══════════════════════════════════════════════════════════════
#  Stylesheet (built from tokens so dark + light stay consistent)
# ═══════════════════════════════════════════════════════════════


def _stylesheet(name: str) -> str:
    t = THEMES[name]
    return f"""
    QWidget {{ background: {t['bg']}; }}
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {t['bg_base']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 5px; padding: 5px 8px;
        selection-background-color: {t['accent']}; selection-color: {t['accent_text']};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {t['border_strong']};
    }}
    QLineEdit:disabled, QTextEdit:disabled {{
        color: {t['text_faint']};
    }}
    QComboBox {{
        background-color: {t['bg_surface']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 5px; padding: 4px 10px;
        min-height: 20px;
    }}
    QComboBox:hover, QComboBox:focus {{ border: 1px solid {t['border_strong']}; }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox::down-arrow {{ image: none; width: 0; height: 0; }}
    QComboBox QAbstractItemView {{
        background-color: {t['bg_surface']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 4px; padding: 4px;
        selection-background-color: {t['accent']}; selection-color: {t['accent_text']};
        outline: 0;
    }}
    QCheckBox {{ color: {t['text']}; spacing: 6px; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 3px; }}
    QSpinBox, QDoubleSpinBox {{
        background-color: {t['bg_base']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 5px; padding: 3px 6px;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {t['border_strong']}; }}
    QPushButton {{
        background-color: {t['bg_surface']}; color: {t['text']};
        border: 1px solid {t['border_subtle']}; border-radius: 6px;
        padding: 6px 14px; font-size: 12px;
    }}
    QPushButton:hover {{ background-color: {t['bg_hover_strong']}; border-color: {t['border']}; }}
    QPushButton:pressed {{ background-color: {t['bg_pressed']}; }}
    QPushButton:disabled {{ color: {t['text_faint']}; }}
    QToolButton {{
        color: {t['text_dim']}; background: transparent; border-radius: 5px;
        padding: 4px 10px; font-size: 12px;
    }}
    QToolButton:hover {{ background: {t['bg_hover']}; color: {t['text']}; }}
    QToolButton:checked {{ background: {t['accent_dim']}; color: {t['accent']}; }}
    QGroupBox {{
        color: {t['text_dim']}; border: 1px solid {t['border']}; border-radius: 8px;
        margin-top: 14px; padding-top: 18px; font-weight: bold;
    }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}
    QLabel {{ background: transparent; color: {t['text']}; }}
    QTableWidget {{
        background-color: {t['bg_base']}; color: {t['text']};
        gridline-color: {t['border']}; border: 1px solid {t['border']}; border-radius: 6px;
    }}
    QTableWidget::item {{ padding: 4px; }}
    QTableWidget::item:selected {{
        background-color: {t['accent']}; color: {t['accent_text']};
    }}
    QHeaderView::section {{
        background-color: {t['bg_surface']}; color: {t['text_dim']};
        border: none; border-bottom: 1px solid {t['border']};
        padding: 6px 8px; font-weight: bold;
    }}
    QListWidget {{
        background-color: {t['bg_base']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 6px; padding: 4px;
        outline: 0;
    }}
    QListWidget::item {{ padding: 5px 8px; border-radius: 4px; }}
    QListWidget::item:selected {{
        background-color: {t['accent']}; color: {t['accent_text']};
    }}
    QListWidget::item:hover {{ background-color: {t['bg_hover']}; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{
        background: transparent; width: 10px; margin: 2px; border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: {t['border']}; border-radius: 5px; min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {t['text_muted']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{
        background: transparent; height: 10px; margin: 2px; border-radius: 5px;
    }}
    QScrollBar::handle:horizontal {{
        background: {t['border']}; border-radius: 5px; min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {t['text_muted']}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QStatusBar {{
        background: {t['bg_elevated']}; color: {t['text_muted']};
        border-top: 1px solid {t['border']};
    }}
    QStatusBar QLabel {{ color: {t['text_muted']}; }}
    QToolBar {{
        background: {t['bg_elevated']}; border-bottom: 1px solid {t['border']};
        spacing: 4px; padding: 4px 8px;
    }}
    QSplitter::handle {{ background: {t['border_subtle']}; }}
    QSplitter::handle:hover {{ background: {t['border_strong']}; }}
    QMenu {{
        background-color: {t['bg_surface']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 6px; padding: 4px;
    }}
    QMenu::item {{ padding: 6px 22px; border-radius: 4px; }}
    QMenu::item:selected {{ background-color: {t['accent']}; color: {t['accent_text']}; }}
    QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 8px; }}
    QToolTip {{
        background-color: {t['bg_surface']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 4px; padding: 4px 8px;
    }}
    QDialog {{ background: {t['bg']}; }}
    QMessageBox {{ background: {t['bg']}; }}
    QMessageBox QLabel {{ color: {t['text']}; }}
    QFileDialog {{ background: {t['bg']}; }}
    """


def apply(app, name: str) -> None:
    global _current
    name = name if name in _PALETTES else "dark"
    _current = name
    app.setPalette(_PALETTES[name]())
    app.setStyleSheet(_stylesheet(name))
    for cb in list(_listeners):
        try:
            cb()
        except Exception as exc:  # pragma: no cover - never let styling crash the app
            print(f"[theme] restyle callback failed: {exc}")
