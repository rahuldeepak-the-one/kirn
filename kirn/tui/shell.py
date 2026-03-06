"""kirn/tui/shell.py — Run real shell commands via subprocess and stream output."""

import subprocess
import os
import shlex


def run_shell_command(command: str, cwd: str | None = None) -> tuple[int, str]:
    """
    Execute a shell command in the current working directory using a pseudo-terminal (PTY)
    so that programs output their native ANSI colors (e.g. `ls`, `git`).
    """
    import pty
    import termios
    import struct
    import fcntl
    import select
    
    target_cwd = cwd or os.getcwd()
    
    try:
        pid, fd = pty.fork()
    except OSError as e:
        msg = f"PTY fork failed: {e}"
        print(msg)
        return 1, msg

    if pid == 0:
        # Child process
        os.chdir(target_cwd)
        # We use standard sh/bash
        os.execlp("sh", "sh", "-c", command)
        os._exit(1)
    else:
        # Parent process
        output_data = bytearray()
        try:
            while True:
                # Use select to read without blocking indefinitely
                r, _, _ = select.select([fd], [], [])
                if fd in r:
                    try:
                        data = os.read(fd, 1024)
                    except OSError:
                        # PTY closed (EIO on Linux)
                        break
                    if not data:
                        break
                    
                    # Print live directly to real stdout so user sees colors immediately
                    os.write(1, data)
                    output_data.extend(data)
        finally:
            os.close(fd)
            
        _, exit_status = os.waitpid(pid, 0)
        exit_code = os.waitstatus_to_exitcode(exit_status) if hasattr(os, 'waitstatus_to_exitcode') else (exit_status >> 8)
        
        # We still return the raw output (with ANSI codes) for Kirn to analyze if it fails
        return exit_code, output_data.decode(errors='replace')


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
