"""kirn/platform.py — OS / environment detection."""

import subprocess


def _is_termux() -> bool:
    """Detect if running inside Termux on Android."""
    return "com.termux" in (subprocess.getoutput("echo $PREFIX") or "")


# Set once at import time — used throughout the package
ON_ANDROID: bool = _is_termux()
