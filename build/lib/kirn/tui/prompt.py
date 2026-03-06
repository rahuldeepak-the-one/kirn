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
from prompt_toolkit.completion import Completer, PathCompleter

from kirn.config import MODEL, SYSTEM_PROMPT, THEME
from kirn.platform import ON_ANDROID
from kirn.tools import TOOLS, TOOL_HANDLERS
from kirn.themes import get_theme
from kirn.tui.mode import detect_mode
from kirn.tui.shell import run_shell_command, resolve_cd


# ─── Load active theme ────────────────────────────────────────────────────────

theme = get_theme(THEME)


def _make_prompt(cwd: str) -> HTML:
    short_cwd = cwd.replace(os.path.expanduser("~"), "~")
    return HTML(
        f'<path>{short_cwd}</path> '
        f'<prompt>kirn ❯</prompt> '
    )


# ─── Tab completer ────────────────────────────────────────────────────────────

class KirnCompleter(Completer):
    """Path completion triggered on Tab."""
    def __init__(self):
        self._path_completer = PathCompleter(expanduser=True)

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        tokens = text.split()
        if not tokens:
            return
        if text.endswith(" ") or len(tokens) >= 2:
            partial = "" if text.endswith(" ") else tokens[-1]
            from prompt_toolkit.document import Document
            sub_doc = Document(partial)
            for completion in self._path_completer.get_completions(sub_doc, complete_event):
                yield completion


# ─── AI helpers ───────────────────────────────────────────────────────────────

def _ai_query(question: str, messages: list) -> None:
    """Send a plain question to the LLM and print the answer."""
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
        print(theme.ai_reply(reply))
        print(theme.ai_timing(elapsed))
    except Exception as e:
        messages.pop()
        print(theme.ai_error(str(e)))


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
        print(theme.ai_error(str(e)))
        return

    elapsed = time.time() - t0
    msg = response["message"]
    messages.append(msg)

    if msg.get("tool_calls"):
        for tc in msg["tool_calls"]:
            func_name = tc["function"]["name"]
            func_args = tc["function"]["arguments"]
            print(theme.tool_call(func_name, json.dumps(func_args)))
            handler = TOOL_HANDLERS.get(func_name)
            result = handler(func_args) if handler else f"Unknown tool: {func_name}"
            print(theme.tool_result(result))
            messages.append({"role": "tool", "content": result})

        # Follow-up
        try:
            t1 = time.time()
            fu = ollama.chat(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            )
            elapsed_fu = time.time() - t1
            fu_msg = fu["message"]
            messages.append(fu_msg)
            if fu_msg.get("content"):
                print(theme.ai_reply(fu_msg["content"]))
                print(theme.ai_timing_dual(elapsed, elapsed_fu))
        except Exception:
            pass
    elif msg.get("content"):
        print(theme.ai_reply(msg["content"]))
        print(theme.ai_timing(elapsed))


def _ai_explain_error(command: str, output: str, exit_code: int, messages: list) -> None:
    """Auto-ask AI to explain a shell command failure."""
    prompt = (
        f"The shell command `{command}` failed with exit code {exit_code}.\n"
        f"Output:\n{output.strip()}\n\n"
        "Explain this error concisely (1-2 sentences max).\n"
        "1. If it looks like a typo of a common Linux command (like 'wd' for 'pwd'), YOU MUST suggest the correct command.\n"
        "2. If the user was asking a natural language question, remind them to start with `?`."
    )
    print(theme.error_explain_header())
    messages_copy = messages + [{"role": "user", "content": prompt}]
    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages_copy,
        )
        reply = response["message"].get("content", "")
        print(theme.ai_reply(reply))
        print()
    except Exception as e:
        print(theme.dim(f"   (AI unavailable: {e})") + "\n")


# ─── Main loop ────────────────────────────────────────────────────────────────

def run_terminal() -> None:
    """Main Kirn terminal loop."""
    device = "Android/Termux" if ON_ANDROID else "Linux"
    print(theme.banner(MODEL, device))

    # Build prompt_toolkit style from theme
    style_dict = {
        "prompt":       "#4fc3f7 bold",
        "path":         "#546e7a",
    }
    style_dict.update(theme.prompt_style)
    kirn_style = Style.from_dict(style_dict)

    history_file = os.path.expanduser("~/.kirn_history")
    session: PromptSession = PromptSession(
        history=FileHistory(history_file),
        auto_suggest=AutoSuggestFromHistory(),
        completer=KirnCompleter(),
        complete_while_typing=False,
        style=kirn_style,
    )

    cwd = os.getcwd()
    messages: list[dict] = []

    while True:
        try:
            user_input = session.prompt(_make_prompt(cwd)).strip()
        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            print("\n" + theme.bye())
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print(theme.bye())
            break

        mode = detect_mode(user_input)

        if mode == "ai_query":
            _ai_query(user_input, messages)

        elif mode == "ai_tool":
            _ai_tool(user_input, messages)

        else:
            new_cwd = resolve_cd(user_input, cwd)
            if new_cwd is not None:
                cwd = new_cwd
                os.chdir(cwd)
            else:
                exit_code, output = run_shell_command(user_input, cwd=cwd)
                if exit_code != 0:
                    _ai_explain_error(user_input, output, exit_code, messages)
