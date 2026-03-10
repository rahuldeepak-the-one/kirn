"""kirn/tools/memory.py — Kirn Semantic Memory Tool.

Allows Kirn to retrieve past successful commands from its own memory json log.
"""

from kirn.memory import search_memory as _search_memory


def search_memory(query: str) -> str:
    """
    Search Kirn's semantic memory log for past commands and solutions.
    Use this to remember how to do things on the user's system (e.g., build commands, server paths).
    """
    return _search_memory(query)
