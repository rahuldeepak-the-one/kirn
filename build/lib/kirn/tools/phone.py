"""kirn/tools/phone.py — phone tool: dial a number via Termux:API."""

import subprocess
from kirn.platform import ON_ANDROID


def handle_phone(phone_number: str) -> str:
    """Dial a phone number."""
    cleaned = "".join(c for c in phone_number if c.isdigit() or c == "+")
    if not cleaned:
        return f"Invalid phone number: '{phone_number}'"

    if not ON_ANDROID:
        return f"[Linux] Would dial {cleaned}. This only works on Android/Termux."

    try:
        result = subprocess.run(
            ["termux-telephony-call", cleaned],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return f"Dialing {cleaned}..."
        return f"Failed to dial: {result.stderr.strip()}"
    except FileNotFoundError:
        return "termux-telephony-call not found. Run: pkg install termux-api"
    except Exception as e:
        return f"Error dialing: {e}"
