"""kirn/tools/app.py — open_app tool: dynamic app discovery and launching."""

import subprocess
from kirn.platform import ON_ANDROID


# ─── Alias tables (friendly name → binary/package keyword) ───────────────────
# Only needed for names that don't match a binary or package directly.

LINUX_ALIASES: dict[str, str] = {
    "browser":      "google-chrome",
    "chrome":       "google-chrome",
    "brave":        "brave-browser",
    "files":        "nautilus",
    "terminal":     "gnome-terminal",
    "text editor":  "gedit",
    "vscode":       "code",
}

ANDROID_ALIASES: dict[str, str] = {
    "browser":  "chrome",
    "camera":   "camera",
    "gallery":  "photos",
    "files":    "documentsui",
    "messages": "messaging",
    "maps":     "maps",
}


# ─── Discovery helpers ────────────────────────────────────────────────────────

def _linux_find_binary(name: str) -> str | None:
    """Resolve a friendly app name to a launchable binary on Linux."""
    candidate = LINUX_ALIASES.get(name, name)

    # Check alias candidate on PATH
    if subprocess.run(["which", candidate], capture_output=True).returncode == 0:
        return candidate

    # Check original name on PATH
    if subprocess.run(["which", name], capture_output=True).returncode == 0:
        return name

    # Search .desktop files by Name= field
    desktop_dirs = [
        "/usr/share/applications",
        "/usr/local/share/applications",
        f"/home/{subprocess.getoutput('whoami')}/.local/share/applications",
    ]
    for d in desktop_dirs:
        try:
            matches = subprocess.run(
                ["grep", "-ril", f"Name={name}", d],
                capture_output=True, text=True
            )
            for desktop_file in matches.stdout.strip().splitlines():
                exec_line = subprocess.run(
                    ["grep", "-i", "^Exec=", desktop_file],
                    capture_output=True, text=True
                ).stdout.strip()
                if exec_line:
                    binary = exec_line.split("=", 1)[1].split()[0]
                    binary = binary.replace("%U", "").replace("%F", "").strip()
                    return binary
        except Exception:
            continue
    return None


def _android_find_package(name: str) -> str | None:
    """Fuzzy-match a friendly name to an installed Android package."""
    keyword = ANDROID_ALIASES.get(name, name)
    result = subprocess.run(["pm", "list", "packages"], capture_output=True, text=True)
    packages = [
        line.replace("package:", "").strip()
        for line in result.stdout.splitlines()
        if keyword.lower() in line.lower()
    ]
    return sorted(packages, key=len)[0] if packages else None


# ─── Tool handler ─────────────────────────────────────────────────────────────

def handle_open_app(app_name: str, url: str = "") -> str:
    """Dynamically discover and open any application by name."""
    key = app_name.strip().lower()
    url = url.strip()

    if ON_ANDROID:
        if url:
            package = _android_find_package(key)
            cmd = ["am", "start", "-a", "android.intent.action.VIEW", "-d", url]
            if package:
                cmd += ["-p", package]
        else:
            package = _android_find_package(key)
            if not package:
                return (f"Could not find an installed app matching '{app_name}'. "
                        "Make sure it's installed on your device.")
            cmd = ["monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"]
    else:
        binary = _linux_find_binary(key)
        if not binary:
            return (f"Could not find an app matching '{app_name}' on this system. "
                    "Try installing it or using its exact binary name.")
        cmd = [binary]
        if url:
            cmd.append(url)

    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        msg = f"Successfully opened '{app_name}'"
        if url:
            msg += f" with URL: {url}"
        return msg + "."
    except FileNotFoundError:
        return f"Failed to launch '{app_name}' — binary not found on PATH."
    except Exception as e:
        return f"Error opening '{app_name}': {e}"
