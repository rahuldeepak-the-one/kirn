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

# Standalone greetings / conversational words — should go to AI, not shell
_GREETINGS = frozenset([
    "hi", "hello", "hey", "yo", "sup", "howdy", "hiya",
    "thanks", "thank", "thankyou", "cheers",
    "bye", "goodbye", "cya", "later",
    "good", "morning", "evening", "night", "afternoon",
])


def detect_mode(text: str) -> str:
    """
    Returns one of:
      "ai_query"       — user is asking a natural-language question (prefix: ?)
      "ai_tool"        — user wants Kirn to perform an action (open, call, etc.)
      "ai_command_gen" — user wants Kirn to generate a shell command
      "shell"          — everything else → pass to the underlying shell
    """
    stripped = text.strip()

    # Explicit AI prefix
    if stripped.startswith("?"):
        return "ai_query"

    # Command generation prefix
    if stripped.lower().startswith("command "):
        return "ai_command_gen"

    # Tool action patterns (open X, call X, launch X)
    if _TOOL_PATTERNS.match(stripped):
        return "ai_tool"

    # All words are greetings/conversational → AI query, not shell
    words = [w.lower().rstrip("?!.,") for w in stripped.split()]
    if words and all(w in _GREETINGS for w in words):
        return "ai_query"

    # Starts with a natural-language interrogative → AI query
    if words and words[0] in _NATURAL_LANGUAGE_WORDS:
        return "ai_query"

    # Default: real shell command
    return "shell"
