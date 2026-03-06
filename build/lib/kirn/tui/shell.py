"""kirn/tui/shell.py — Run real shell commands via subprocess and stream output."""

import subprocess
import os
import shlex


def run_shell_command(command: str, cwd: str | None = None) -> tuple[int, str]:
    """
    Execute a shell command in the current working directory.
    Streams output live to stdout and returns (exit_code, combined_output).
    """
    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd or os.getcwd(),
            env=os.environ.copy(),
        )
        output_lines = []
        for line in proc.stdout:
            print(line, end="", flush=True)
            output_lines.append(line)
        proc.wait()
        return proc.returncode, "".join(output_lines)
    except Exception as e:
        msg = f"Shell error: {e}"
        print(msg)
        return 1, msg


def resolve_cd(command: str, cwd: str) -> str | None:
    """
    Handle `cd` specially — subprocess can't change the parent's cwd,
    so we track it ourselves. Returns new cwd string, or None if not a cd command.
    """
    parts = shlex.split(command)
    if not parts or parts[0] != "cd":
        return None

    target = parts[1] if len(parts) > 1 else os.path.expanduser("~")
    # Handle relative and absolute paths
    new_cwd = os.path.realpath(os.path.join(cwd, target))
    if os.path.isdir(new_cwd):
        return new_cwd
    print(f"cd: no such directory: {target}")
    return cwd  # unchanged
