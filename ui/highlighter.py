"""Python syntax highlighter for the live preview pane."""

from __future__ import annotations

from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

import theme

_KEYWORDS = frozenset(
    {
        "import",
        "from",
        "as",
        "def",
        "class",
        "return",
        "if",
        "else",
        "elif",
        "for",
        "while",
        "in",
        "not",
        "and",
        "or",
        "True",
        "False",
        "None",
        "with",
        "lambda",
        "yield",
        "pass",
        "break",
        "continue",
        "try",
        "except",
        "finally",
        "raise",
    }
)


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._kw = QTextCharFormat()
        self._str = QTextCharFormat()
        self._cmt = QTextCharFormat()
        self._num = QTextCharFormat()
        self._apply_theme()

    def _apply_theme(self) -> None:
        t = theme.tokens()
        self._kw.setForeground(QColor(t["kw"]))
        self._kw.setFontWeight(QFont.Weight.Bold)
        self._str.setForeground(QColor(t["str"]))
        self._cmt.setForeground(QColor(t["cmt"]))
        self._cmt.setFontItalic(True)
        self._num.setForeground(QColor(t["num"]))
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        i, n = 0, len(text)
        in_str, str_char = False, ""
        tok_start, tok_chars = 0, []

        def flush():
            nonlocal tok_chars, tok_start
            word = "".join(tok_chars)
            if word:
                if word in _KEYWORDS:
                    self.setFormat(tok_start, len(word), self._kw)
                elif word[0].isdigit() or (
                    word[0] == "-" and len(word) > 1 and word[1].isdigit()
                ):
                    self.setFormat(tok_start, len(word), self._num)
            tok_chars = []

        while i < n:
            ch = text[i]
            if not in_str and ch == "#":
                flush()
                self.setFormat(i, n - i, self._cmt)
                return
            if not in_str and ch in ('"', "'"):
                flush()
                in_str, str_char = True, ch
                s = i
                i += 1
                while i < n:
                    if text[i] == "\\" and i + 1 < n:
                        i += 2
                        continue
                    if text[i] == str_char:
                        self.setFormat(s, i - s + 1, self._str)
                        in_str = False
                        i += 1
                        break
                    i += 1
                continue
            if ch.isalnum() or ch in ("_", "."):
                if not tok_chars:
                    tok_start = i
                tok_chars.append(ch)
            else:
                flush()
            i += 1
        flush()
