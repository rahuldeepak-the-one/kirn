"""kirn/tui/prompt.py — Main Kirn terminal loop using prompt_toolkit."""

import os
import sys
import time
import json
import getpass
import threading
import itertools
import subprocess

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


# ─── Session Statistics ───────────────────────────────────────────────────────

class SessionStats:
    """Track usage statistics for the current session."""
    def __init__(self):
        self.start_time = time.time()
        self.shell_cmds = 0
        self.ai_queries = 0
        self.tool_actions = 0
        self.errors_caught = 0


# ─── Git integration ─────────────────────────────────────────────────────────

def _get_git_info(cwd: str) -> tuple[str, bool]:
    """Fast check for current git branch and dirty state.
    Returns (branch_name, is_dirty). Empty string if not in a repo.
    """
    try:
        branch_res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=0.15
        )
        if branch_res.returncode != 0 or not branch_res.stdout.strip():
            return "", False

        branch = branch_res.stdout.strip()

        dirty_res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=0.15
        )
        is_dirty = bool(dirty_res.stdout.strip())
        return branch, is_dirty
    except Exception:
        return "", False


# ─── Prompt builder ───────────────────────────────────────────────────────────

_last_exit_code = 0

def _make_prompt(cwd: str) -> HTML:
    user = getpass.getuser()
    short_cwd = cwd.replace(os.path.expanduser("~"), "~")

    # Git info
    branch, dirty = _get_git_info(cwd)
    git_html = ""
    if branch:
        dirty_flag = "*" if dirty else ""
        git_html = f' <git> {branch}{dirty_flag}</git>'

    # Exit code indicator
    if _last_exit_code == 0:
        status_html = '<exit-ok>✓</exit-ok>'
    else:
        status_html = f'<exit-fail>✗ {_last_exit_code}</exit-fail>'

    return HTML(
        f'<user>{user}</user>'
        f'<at>@</at>'
        f'<host>kirn</host> '
        f'<path>{short_cwd}</path>'
        f'{git_html} '
        f'{status_html} '
        f'<prompt>❯</prompt> '
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


# ─── Spinner with contextual animations ──────────────────────────────────────

SPINNER_STYLES = {
    "dots":     ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
    "moon":     ['◐', '◓', '◑', '◒'],
    "progress": ['▰▱▱▱▱', '▰▰▱▱▱', '▰▰▰▱▱', '▰▰▰▰▱', '▰▰▰▰▰', '▱▰▰▰▰', '▱▱▰▰▰', '▱▱▱▰▰', '▱▱▱▱▰', '▱▱▱▱▱'],
    "pulse":    ['○', '◎', '●', '◎'],
}


class Spinner:
    """A context manager to display a themed, animated spinner in the terminal."""
    def __init__(self, message="Thinking...", style="dots"):
        self.message = theme.dim(message)
        frames = SPINNER_STYLES.get(style, SPINNER_STYLES["dots"])
        self.spinner = itertools.cycle(frames)
        self.stop_running = threading.Event()
        self.thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        while not self.stop_running.is_set():
            frame = next(self.spinner)
            sys.stdout.write(f"\r{self.message} {theme.ACCENT}{frame}{theme.TEXT}")
            sys.stdout.flush()
            time.sleep(0.12)

    def __enter__(self):
        self.stop_running.clear()
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_running.set()
        self.thread.join()
        sys.stdout.write('\r\x1b[2K')
        sys.stdout.flush()


# ─── AI helpers ───────────────────────────────────────────────────────────────

def _ai_query(question: str, messages: list, stats: SessionStats) -> None:
    """Send a plain question to the LLM and print the answer."""
    clean = question.lstrip("?").strip()
    messages.append({"role": "user", "content": clean})
    stats.ai_queries += 1
    t0 = time.time()
    try:
        with Spinner("Thinking...", style="dots"):
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


def _ai_tool(user_input: str, messages: list, cwd: str, stats: SessionStats) -> None:
    """Send a tool-triggering request to the LLM and execute returned tools iteratively."""
    messages.append({"role": "user", "content": user_input})
    t_start = time.time()

    max_loops = 10
    loops = 0

    while loops < max_loops:
        loops += 1
        try:
            with Spinner("Processing tasks...", style="moon"):
                response = ollama.chat(
                    model=MODEL,
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                    tools=TOOLS,
                )
        except Exception as e:
            if loops == 1:
                messages.pop()
            print(theme.ai_error(str(e)))
            return

        msg = response["message"]
        messages.append(msg)

        if not msg.get("tool_calls"):
            # Check if LLM outputted raw JSON instead of native tool call
            content = msg.get("content", "").strip()
            if content.startswith("```json") and content.endswith("```"):
                import re
                try:
                    raw_json = re.sub(r'```json\n|\n```', '', content)
                    parsed_tc = json.loads(raw_json)
                    if isinstance(parsed_tc, dict) and "name" in parsed_tc:
                        msg["tool_calls"] = [{"function": parsed_tc}]
                except Exception:
                    pass
            elif content.startswith("{") and content.endswith("}") and '"name"' in content:
                try:
                    parsed_tc = json.loads(content)
                    if isinstance(parsed_tc, dict) and "name" in parsed_tc:
                        msg["tool_calls"] = [{"function": parsed_tc}]
                except Exception:
                    pass

        if not msg.get("tool_calls"):
            elapsed = time.time() - t_start
            if msg.get("content"):
                print(theme.ai_reply(msg["content"]))
                print(theme.ai_timing(elapsed))
            break

        for tc in msg["tool_calls"]:
            func_name = tc["function"]["name"]
            func_args = tc["function"]["arguments"]
            print(theme.tool_call(func_name, json.dumps(func_args)))
            stats.tool_actions += 1

            if func_name == "run_terminal_command":
                from kirn.tools.terminal import handle_run_command
                result = handle_run_command(func_args.get("command", ""), cwd=cwd)
            else:
                handler = TOOL_HANDLERS.get(func_name)
                result = handler(func_args) if handler else f"Unknown tool: {func_name}"

            print(theme.tool_result(result))
            messages.append({"role": "tool", "content": result})

    if loops == max_loops:
        print(theme.ai_error("Max autonomous iterations reached. Stopping to prevent infinite loop."))


def _ai_explain_error(command: str, output: str, exit_code: int, messages: list, stats: SessionStats) -> None:
    """Auto-ask AI to explain a shell command failure."""
    stats.errors_caught += 1
    prompt = (
        f"The shell command `{command}` failed with exit code {exit_code}.\n"
        f"Output:\n{output.strip()}\n\n"
        "Analyze this error and provide a response in the following strict format:\n\n"
        "**Summary:** [1-2 sentence explanation of what went wrong]\n\n"
        "**Try these commands:**\n"
        "- `[command 1]`\n"
        "- `[command 2]`\n\n"
        "If it looks like a typo, suggest the corrected command. If the user was asking a natural language question, remind them to start with `?`."
    )
    print(theme.error_explain_header())
    messages_copy = messages + [{"role": "user", "content": prompt}]
    try:
        with Spinner("Interpreting error...", style="pulse"):
            response = ollama.chat(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages_copy,
            )
        reply = response["message"].get("content", "")
        print(theme.ai_reply(reply))
        print()
    except Exception as e:
        print(theme.dim(f"   (AI unavailable: {e})") + "\n")


def _ai_command_gen(user_input: str, messages: list, stats: SessionStats) -> None:
    """Ask the LLM to generate a shell command without executing it."""
    clean = user_input[len("command "):].strip()
    prompt = f"Provide ONLY the shell command to achieve this: {clean}. Do not use any markdown formatting or backticks around the command. Do not explain anything."

    stats.ai_queries += 1
    messages_copy = messages + [{"role": "user", "content": prompt}]
    t0 = time.time()
    try:
        with Spinner("Generating command...", style="progress"):
            response = ollama.chat(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages_copy,
            )
        elapsed = time.time() - t0
        reply = response["message"].get("content", "").strip()
        # Strip markdown codeblocks if the LLM ignores the instruction
        if reply.startswith("```") and reply.endswith("```"):
            lines = reply.split('\n')
            if len(lines) >= 3:
                reply = '\n'.join(lines[1:-1]).strip()
            else:
                reply = reply.strip("`").strip()

        print(theme.ai_reply(reply))
        print(theme.ai_timing(elapsed))
    except Exception as e:
        print(theme.ai_error(str(e)))


# ─── Built-in commands ────────────────────────────────────────────────────────

def _show_history(history_file: str) -> None:
    """Display the last 25 commands from history."""
    try:
        with open(history_file, "r") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        recent = lines[-25:] if len(lines) > 25 else lines
        start_idx = len(lines) - len(recent) + 1
        print()
        for i, entry in enumerate(recent, start=start_idx):
            print(theme.history_entry(i, entry))
        print()
    except FileNotFoundError:
        print(theme.dim("  No history yet.\n"))


# ─── Main loop ────────────────────────────────────────────────────────────────

def run_terminal() -> None:
    """Main Kirn terminal loop."""
    global _last_exit_code

    device = "Android/Termux" if ON_ANDROID else "Linux"
    print(theme.banner(MODEL, device))

    # Build prompt_toolkit style from theme
    style_dict = {
        "prompt":       "#4fc3f7 bold",
        "path":         "#78909c",
        "git":          "#fbc02d",
        "user":         "#ce93d8",
        "at":           "#546e7a",
        "host":         "#4fc3f7",
        "exit-ok":      "#a5d6a7",
        "exit-fail":    "#ef5350",
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
    stats = SessionStats()

    while True:
        try:
            user_input = session.prompt(_make_prompt(cwd)).strip()
        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            duration = time.time() - stats.start_time
            print("\n" + theme.session_summary(duration, stats.shell_cmds, stats.ai_queries, stats.tool_actions, stats.errors_caught))
            print(theme.bye())
            break

        if not user_input:
            continue

        # Built-in commands
        if user_input.lower() in ("exit", "quit"):
            duration = time.time() - stats.start_time
            print(theme.session_summary(duration, stats.shell_cmds, stats.ai_queries, stats.tool_actions, stats.errors_caught))
            print(theme.bye())
            break

        if user_input.lower() == "clear":
            sys.stdout.write('\033[2J\033[H')
            sys.stdout.flush()
            continue

        if user_input.lower() == "history":
            _show_history(history_file)
            continue

        mode = detect_mode(user_input)

        if mode == "ai_query":
            _ai_query(user_input, messages, stats)

        elif mode == "ai_command_gen":
            _ai_command_gen(user_input, messages, stats)

        elif mode == "ai_tool":
            _ai_tool(user_input, messages, cwd, stats)

        else:
            new_cwd = resolve_cd(user_input, cwd)
            if new_cwd is not None:
                cwd = new_cwd
                os.chdir(cwd)
                _last_exit_code = 0
            else:
                stats.shell_cmds += 1
                exit_code, output = run_shell_command(user_input, cwd=cwd)
                _last_exit_code = exit_code
                if exit_code != 0:
                    _ai_explain_error(user_input, output, exit_code, messages, stats)

    # Clean up and unload the Ollama model from memory when Kirn exits
    try:
        ollama.generate(model=MODEL, prompt="", keep_alive=0)
    except Exception:
        pass
