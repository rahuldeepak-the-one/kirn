"""kirn/tui/prompt.py — Main Kirn terminal loop using prompt_toolkit."""

import os
import time
import json

import ollama
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML

from kirn.config import MODEL, SYSTEM_PROMPT
from kirn.platform import ON_ANDROID
from kirn.tools import TOOLS, TOOL_HANDLERS
from kirn.tui.mode import detect_mode
from kirn.tui.shell import run_shell_command, resolve_cd


# ─── Prompt style (Warp-like) ─────────────────────────────────────────────────

KIRN_STYLE = Style.from_dict({
    "prompt":       "#00d7ff bold",      # cyan
    "path":         "#888888",           # dim grey
    "at":           "#555555",
    "error":        "#ff5555 bold",
    "ai":           "#a8ff78",           # green
})


def _make_prompt(cwd: str) -> HTML:
    short_cwd = cwd.replace(os.path.expanduser("~"), "~")
    return HTML(
        f'<path>{short_cwd}</path> '
        f'<prompt>kirn ❯</prompt> '
    )


# ─── AI helpers ───────────────────────────────────────────────────────────────

def _ai_query(question: str, messages: list) -> None:
    """Send a plain question to the LLM and print the answer."""
    # Strip leading ? if present
    clean = question.lstrip("?").strip()
    messages.append({"role": "user", "content": clean})
    t0 = time.time()
    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        )
        elapsed = time.time() - t0
        reply = response["message"].get("content", "")
        messages.append(response["message"])
        print(f"\n🤖 {reply}")
        print(f"   [⏱️  {elapsed:.2f}s]\n")
    except Exception as e:
        messages.pop()
        print(f"\n❌ AI error: {e}\n")


def _ai_tool(user_input: str, messages: list) -> None:
    """Send a tool-triggering request to the LLM and execute returned tools."""
    messages.append({"role": "user", "content": user_input})
    t0 = time.time()
    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            tools=TOOLS,
        )
    except Exception as e:
        messages.pop()
        print(f"\n❌ AI error: {e}\n")
        return

    elapsed = time.time() - t0
    msg = response["message"]
    messages.append(msg)

    if msg.get("tool_calls"):
        for tc in msg["tool_calls"]:
            func_name = tc["function"]["name"]
            func_args = tc["function"]["arguments"]
            print(f"\n⚙️  {func_name}({json.dumps(func_args)})")
            handler = TOOL_HANDLERS.get(func_name)
            result = handler(func_args) if handler else f"Unknown tool: {func_name}"
            print(f"   → {result}")
            messages.append({"role": "tool", "content": result})

        # Follow-up
        try:
            fu = ollama.chat(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            )
            fu_msg = fu["message"]
            messages.append(fu_msg)
            if fu_msg.get("content"):
                print(f"\n🤖 {fu_msg['content']}\n")
        except Exception:
            pass
    elif msg.get("content"):
        print(f"\n🤖 {msg['content']}")
        print(f"   [⏱️  {elapsed:.2f}s]\n")


def _ai_explain_error(command: str, output: str, exit_code: int, messages: list) -> None:
    """Auto-ask AI to explain a shell command failure."""
    prompt = (
        f"The shell command `{command}` failed with exit code {exit_code}.\n"
        f"Output:\n{output.strip()}\n\n"
        "Briefly explain what went wrong and how to fix it."
    )
    print("\n🤖 Kirn is explaining the error...\n")
    messages_copy = messages + [{"role": "user", "content": prompt}]
    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages_copy,
        )
        reply = response["message"].get("content", "")
        print(f"🤖 {reply}\n")
    except Exception as e:
        print(f"   (AI unavailable: {e})\n")


# ─── Main loop ────────────────────────────────────────────────────────────────

def run_terminal() -> None:
    """Main Kirn terminal loop."""
    print("═" * 48)
    print("  ⚡ KIRN — AI Terminal")
    print(f"  Model : {MODEL}")
    print(f"  Device: {'Android/Termux' if ON_ANDROID else 'Linux'}")
    print("  ? <question>  →  ask AI")
    print("  open/call <x>  →  AI action")
    print("  everything else  →  real shell")
    print("  Ctrl+C / exit  →  quit")
    print("═" * 48)
    print()

    history_file = os.path.expanduser("~/.kirn_history")
    session: PromptSession = PromptSession(
        history=FileHistory(history_file),
        auto_suggest=AutoSuggestFromHistory(),
        style=KIRN_STYLE,
    )

    cwd = os.getcwd()
    messages: list[dict] = []   # AI conversation context

    while True:
        try:
            user_input = session.prompt(_make_prompt(cwd)).strip()
        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            print("\nBye! 👋")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Bye! 👋")
            break

        mode = detect_mode(user_input)

        if mode == "ai_query":
            _ai_query(user_input, messages)

        elif mode == "ai_tool":
            _ai_tool(user_input, messages)

        else:
            # Real shell command
            # Handle cd specially (can't change cwd in a subprocess)
            new_cwd = resolve_cd(user_input, cwd)
            if new_cwd is not None:
                cwd = new_cwd
                os.chdir(cwd)
            else:
                exit_code, output = run_shell_command(user_input, cwd=cwd)
                if exit_code != 0:
                    _ai_explain_error(user_input, output, exit_code, messages)
