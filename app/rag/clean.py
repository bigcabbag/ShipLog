"""U-014：入库前轻清洗（去多余空行 / 行尾空白 / HTML 注释）。"""

from __future__ import annotations

import re

_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_MULTI_BLANK_RE = re.compile(r"\n{3,}")
_TRAILING_WS_RE = re.compile(r"[ \t]+\n")


def clean_text(text: str) -> str:
    """轻量清洗：不改语义结构，只压噪声。"""
    if not text:
        return ""
    out = text.replace("\r\n", "\n").replace("\r", "\n")
    out = _HTML_COMMENT_RE.sub("", out)
    out = _TRAILING_WS_RE.sub("\n", out)
    out = _MULTI_BLANK_RE.sub("\n\n", out)
    return out.strip()
