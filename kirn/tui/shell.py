"""kirn/tui/shell.py — Run real shell commands via subprocess and stream output."""

import subprocess
import os
import shlex


def run_shell_command(command: str, cwd: str | None = None) -> tuple[int, str]:
    """
    Execute a shell command with a fully interactive pseudo-terminal (PTY).
    This handles raw TTY mode so that interactive tools like `vim` or `htop` work,
    and it captures the output to send to the AI if the command errors.
    """
    import pty
    import tty
    import termios
    import struct
    import fcntl
    import select
    import sys
    
    target_cwd = cwd or os.getcwd()
    
    # Save original TTY attributes so we can restore them later
    try:
        old_tty = termios.tcgetattr(sys.stdin.fileno())
        tty.setraw(sys.stdin.fileno())
    except Exception:
        old_tty = None

    try:
        master_fd, slave_fd = pty.openpty()
    except OSError as e:
        if old_tty:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, old_tty)
        msg = f"PTY fork failed: {e}"
        print(msg)
        return 1, msg

    # Match the child's PTY window size to the parent's actual terminal
    try:
        packed = fcntl.ioctl(sys.stdin.fileno(), termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0))
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, packed)
    except Exception:
        pass

    pid = os.fork()
    if pid == 0:
        # Child process execution
        os.close(master_fd)
        os.setsid()
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        if slave_fd > 2:
            os.close(slave_fd)
            
        os.chdir(target_cwd)
        os.execlp("sh", "sh", "-c", command)
        os._exit(1)
        
    # Parent process loop
    os.close(slave_fd)
    output_data = bytearray()
    
    try:
        while True:
            # multiplex IO between user's keyboard (stdin) and the child command (master_fd)
            r, _, _ = select.select([master_fd, sys.stdin.fileno()], [], [])
            
            # Forward user input to the child command
            if sys.stdin.fileno() in r:
                try:
                    data = os.read(sys.stdin.fileno(), 1024)
                    if not data:
                        break
                    os.write(master_fd, data)
                except OSError:
                    pass
            
            # Forward child command output to the screen AND capture it
            if master_fd in r:
                try:
                    data = os.read(master_fd, 1024)
                    if not data:
                        break
                    os.write(sys.stdout.fileno(), data)
                    output_data.extend(data)
                except OSError:
                    # Child closed PTY (finished execution)
                    break
    finally:
        os.close(master_fd)
        if old_tty is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, old_tty)
            
    _, exit_status = os.waitpid(pid, 0)
    exit_code = os.waitstatus_to_exitcode(exit_status) if hasattr(os, 'waitstatus_to_exitcode') else (exit_status >> 8)
    
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
