from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFontDatabase


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_FONTS_DIR = PROJECT_ROOT / "public" / "fonts"
GOST_COMMON_PATH = PUBLIC_FONTS_DIR / "GOST_Common.ttf"
GOST_ITALIC_PATH = PUBLIC_FONTS_DIR / "GOST_Common Italic.ttf"

GOST_COMMON_FAMILY = "GOST Common"
SYSTEM_SANS_FAMILY = "Sans Serif"
DIMENSION_FONT_MODE_GOST_ITALIC = "gost_common_italic"
DIMENSION_FONT_MODE_GOST_REGULAR = "gost_common_regular"
DIMENSION_FONT_MODE_SANS = "sans_serif"

_fonts_loaded = False


def ensure_app_fonts_loaded() -> None:
    global _fonts_loaded
    if _fonts_loaded:
        return

    for path in (GOST_COMMON_PATH, GOST_ITALIC_PATH):
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))

    _fonts_loaded = True


def dimension_font_choices() -> list[tuple[str, str]]:
    return [
        ("ГОСТ Common Italic", DIMENSION_FONT_MODE_GOST_ITALIC),
        ("ГОСТ Common", DIMENSION_FONT_MODE_GOST_REGULAR),
        ("Системный Sans Serif", DIMENSION_FONT_MODE_SANS),
    ]


def resolve_dimension_font(mode: str | None) -> tuple[str, bool]:
    if mode == DIMENSION_FONT_MODE_GOST_REGULAR:
        return GOST_COMMON_FAMILY, False
    if mode == DIMENSION_FONT_MODE_SANS:
        return SYSTEM_SANS_FAMILY, False
    return GOST_COMMON_FAMILY, True
