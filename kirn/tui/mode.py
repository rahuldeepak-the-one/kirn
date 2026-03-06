"""kirn/tui/mode.py — Detect user intent: shell command, AI query, or AI tool call."""

import re

# Phrases that strongly indicate an AI tool action (not a query)
_TOOL_PATTERNS = re.compile(
    r"^(open|launch|start|run app|call|dial|phone)\s+\S",
    re.IGNORECASE,
)

# Words that look like natural English rather than shell commands
_NATURAL_LANGUAGE_WORDS = frozenset([
    "what", "why", "how", "when", "where", "who", "explain",
    "tell", "describe", "help", "is", "are", "can", "could",
    "does", "do", "will", "would", "show", "give", "list",
])


def detect_mode(text: str) -> str:
    """
    Returns one of:
      "ai_query"  — user is asking a natural-language question (prefix: ?)
      "ai_tool"   — user wants Kirn to perform an action (open, call, etc.)
      "shell"     — everything else → pass to the underlying shell
    """
    stripped = text.strip()

    # Explicit AI prefix
    if stripped.startswith("?"):
        return "ai_query"

    # Tool action patterns (open X, call X, launch X)
    if _TOOL_PATTERNS.match(stripped):
        return "ai_tool"

    # Starts with a natural-language word → treat as AI query
    first_word = stripped.split()[0].lower().rstrip("?!.,") if stripped else ""
    if first_word in _NATURAL_LANGUAGE_WORDS:
        return "ai_query"

    # Default: real shell command
    return "shell"
