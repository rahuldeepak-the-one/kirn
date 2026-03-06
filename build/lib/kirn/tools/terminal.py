"""kirn/tools/terminal.py — run_terminal_command tool: execute shell commands."""

import subprocess


def handle_run_command(command: str) -> str:
    """Execute a shell command and return its output."""
    if not command.strip():
        return "No command provided."
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout.strip()}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr.strip()}\n"
        if not output:
            output = "Command executed successfully with no output."
        return f"Exit code: {result.returncode}\n{output}"
    except subprocess.TimeoutExpired:
        return f"Command timed out after 10 seconds: {command}"
    except Exception as e:
        return f"Error executing command: {e}"
