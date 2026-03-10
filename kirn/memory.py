"""kirn/memory.py — Semantic Command Memory Log.

Provides a persistent JSON-based memory of past successful tasks, the commands
used to solve them, and the outcome. Allows Kirn to remember how to do things
on this specific system.
"""

import os
import json
import time

MEMORY_FILE = os.path.expanduser("~/.kirn_memory.json")


def load_memory() -> list[dict]:
    """Load the memory log from disk."""
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_memory(user_goal: str, commands_run: list[str], outcome: str, cwd: str) -> None:
    """Save a successful interaction to the memory log."""
    # Don't save trivial things
    if not commands_run or len(commands_run) == 0:
        return


    memory = load_memory()
    
    entry = {
        "timestamp": int(time.time()),
        "user_goal": user_goal,
        "commands_run": commands_run,
        "outcome": outcome,
        "cwd": cwd
    }
    
    memory.append(entry)
    
    # Keep only the last 500 entries to prevent bloat
    if len(memory) > 500:
        memory = memory[-500:]
        
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory, f, indent=2)
    except Exception:
        pass


def search_memory(query: str) -> str:
    """
    Search the memory log for keywords related to the query.
    Returns a formatted string of past successful interactions.
    """
    memory = load_memory()
    if not memory:
        return "Memory is empty. No past interactions recorded."

    query_terms = set(word.lower() for word in query.replace("-", " ").split() if len(word) > 2)
    
    results = []
    for entry in memory:
        # Score the entry based on keyword hits in goal or commands
        score = 0
        search_text = (entry.get("user_goal", "") + " " + " ".join(entry.get("commands_run", []))).lower()
        
        for term in query_terms:
            if term in search_text:
                score += 1
                
        if score > 0:
            results.append((score, entry))
            
    if not results:
        return f"No memories found matching query: '{query}'"
        
    # Sort by score (descending), then recency (descending)
    results.sort(key=lambda x: (x[0], x[1].get("timestamp", 0)), reverse=True)
    
    # Return top 5 matches
    top_matches = [entry for _, entry in results[:5]]
    
    output = "Found past interactions in memory:\n\n"
    for i, match in enumerate(top_matches, 1):
        output += f"--- Memory {i} ---\n"
        output += f"Goal: {match.get('user_goal')}\n"
        output += f"Commands Used:\n"
        for cmd in match.get("commands_run", []):
            output += f"  $ {cmd}\n"
        output += f"Outcome: {match.get('outcome')}\n\n"
        
    output += "Note: These are past actions and may contain outdated context. Use them as reference."
    return output
