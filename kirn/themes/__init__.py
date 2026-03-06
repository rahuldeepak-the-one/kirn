"""kirn/themes/__init__.py — Theme loader.

To add a new theme:
  1. Create kirn/themes/your_theme.py
  2. Define a COLORS dict and optional PROMPT_STYLE dict
  3. Add the name to get_theme() below
"""

from kirn.themes.base import Theme


def get_theme(name: str) -> Theme:
    """Load a theme by name. Returns a Theme instance."""
    name = name.strip().lower()

    if name == "interstellar":
        from kirn.themes.interstellar import COLORS, PROMPT_STYLE
        return Theme(name, COLORS, PROMPT_STYLE)

    # Fallback: interstellar
    print(f"⚠️  Theme '{name}' not found, falling back to 'interstellar'")
    from kirn.themes.interstellar import COLORS, PROMPT_STYLE
    return Theme(name, COLORS, PROMPT_STYLE)
