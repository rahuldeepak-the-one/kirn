"""kirn/agent.py — Main AI conversation loop."""

import time
import ollama

from kirn.config import MODEL, SYSTEM_PROMPT
from kirn.platform import ON_ANDROID
from kirn.tools import TOOLS, execute_tool


# Conversational words that should NEVER trigger a tool call
_CONVERSATIONAL = frozenset({
    "hi", "hello", "hey", "howdy", "yo", "sup",
    "thanks", "thank you", "bye", "good morning", "good evening",
})


def _is_conversational(text: str) -> bool:
    words = text.lower().strip().split()
    return all(w in _CONVERSATIONAL for w in words)


def run_assistant() -> None:
    """Main input → LLM → tool-execution loop."""
    print("═" * 44)
    print("  ⚡ KIRN — Your Offline AI Agent")
    print(f"  Model : {MODEL}")
    print(f"  Device: {'Android/Termux' if ON_ANDROID else 'Linux'}")
    print("  Type 'quit' or 'exit' to stop.")
    print("═" * 44)
    print()

    messages: list[dict] = []

    while True:
        # ── Input ──────────────────────────────────────────────────────────────
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye! 👋")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print("Bye! 👋")
            break

        messages.append({"role": "user", "content": user_input})
        conversational = _is_conversational(user_input)

        # ── LLM call ───────────────────────────────────────────────────────────
        t0 = time.time()
        try:
            response = ollama.chat(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                tools=TOOLS,
            )
        except ollama.ResponseError as e:
            print(f"\n❌ Ollama error: {e}")
            print(f"   Is Ollama running?  → ollama serve")
            print(f"   Model pulled?       → ollama pull {MODEL}\n")
            messages.pop()
            continue
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}\n")
            messages.pop()
            continue

        elapsed = time.time() - t0
        msg = response["message"]
        messages.append(msg)

        # ── Tool calls ─────────────────────────────────────────────────────────
        if msg.get("tool_calls") and not conversational:
            for tc in msg["tool_calls"]:
                result = execute_tool(tc)
                messages.append({"role": "tool", "content": result})

            # Follow-up response after tools ran
            try:
                t1 = time.time()
                followup = ollama.chat(
                    model=MODEL,
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                    tools=TOOLS,
                )
                elapsed_fu = time.time() - t1
                fu_msg = followup["message"]
                messages.append(fu_msg)
                if fu_msg.get("content"):
                    print(f"\n🤖 {fu_msg['content']}")
                    print(f"   [⏱️  Initial: {elapsed:.2f}s | Follow-up: {elapsed_fu:.2f}s]\n")
            except Exception:
                pass

        # ── Plain text response ────────────────────────────────────────────────
        elif msg.get("content"):
            print(f"\n🤖 {msg['content']}")
            print(f"   [⏱️  {elapsed:.2f}s]\n")

        else:
            print(f"\n🤖 (no response) [⏱️  {elapsed:.2f}s]\n")
