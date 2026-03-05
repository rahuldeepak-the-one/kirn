"""
Kirn — Your offline AI assistant. Runs on Android (Termux) or Linux.
Uses Ollama with llama3.2:3b for local tool-calling.
"""

import json
import subprocess
import sys
import platform

import ollama


# ─── Configuration ───────────────────────────────────────────────────────────

# MODEL = "qwen2.5:0.5b"
MODEL = "llama3.2:3b"

SYSTEM_PROMPT = (
    "You are Kirn, a sharp and capable offline AI assistant running on the user's device. "
    "You have a confident, no-fluff personality — you get things done. "
    "You have tools available but must use them sparingly and ONLY when the user clearly requests a specific action.\n"
    "DO NOT use any tool for greetings, questions, or casual conversation.\n"
    "TOOL USAGE GUIDE:\n"
    "- open_app: ONLY when user says 'open X' or 'launch X'\n"
    "- phone: ONLY when user says 'call X' or 'dial X'\n"
    "- run_terminal_command: ONLY when user gives a specific shell command to run\n"
    "For everything else — greetings, questions, chat — respond in plain text with NO tool calls."
)


# ─── App name → launch command mapping ───────────────────────────────────────

def _is_termux() -> bool:
    """Detect if we're running inside Termux on Android."""
    return "com.termux" in (subprocess.getoutput("echo $PREFIX") or "")


# ─── Common aliases (friendly name → binary/package keyword) ─────────────────
# Only used for names that don't match any binary directly.
# Everything else is discovered dynamically.

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
    "browser":   "chrome",
    "camera":    "camera",
    "gallery":   "photos",
    "files":     "documentsui",
    "messages":  "messaging",
    "maps":      "maps",
}

ON_ANDROID = _is_termux()


# ─── Dynamic discovery helpers ────────────────────────────────────────────────

def _linux_find_binary(name: str) -> str | None:
    """Try to resolve an app name to a launchable binary on Linux."""
    # 1. Resolve through alias table
    candidate = LINUX_ALIASES.get(name, name)

    # 2. Check if it's directly on PATH
    result = subprocess.run(["which", candidate], capture_output=True, text=True)
    if result.returncode == 0:
        return candidate

    # 3. Also try the original name on PATH (in case alias wasn't in table)
    result = subprocess.run(["which", name], capture_output=True, text=True)
    if result.returncode == 0:
        return name

    # 4. Search .desktop files in /usr/share/applications for app name
    desktop_dirs = ["/usr/share/applications", "/usr/local/share/applications",
                    f"/home/{subprocess.getoutput('whoami')}/.local/share/applications"]
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
                    # Strip "Exec=" prefix and remove %U/%F etc.
                    binary = exec_line.split("=", 1)[1].split()[0]
                    binary = binary.replace("%U", "").replace("%F", "").strip()
                    return binary
        except Exception:
            continue
    return None


def _android_find_package(name: str) -> str | None:
    """Fuzzy-match an app name to an installed Android package."""
    # 1. Check alias table first
    keyword = ANDROID_ALIASES.get(name, name)

    # 2. List all packages and find one whose name contains the keyword
    result = subprocess.run(
        ["pm", "list", "packages"], capture_output=True, text=True
    )
    packages = [
        line.replace("package:", "").strip()
        for line in result.stdout.splitlines()
        if keyword.lower() in line.lower()
    ]
    if packages:
        # Prefer shorter/more specific package names
        return sorted(packages, key=len)[0]
    return None


# ─── Tool handler ─────────────────────────────────────────────────────────────

def handle_open_app(app_name: str, url: str = "") -> str:
    """Dynamically discover and open any application by name."""
    key = app_name.strip().lower()
    url = url.strip()

    if ON_ANDROID:
        if url:
            # Open a URL — let Android pick the right browser or use specified one
            package = _android_find_package(key)
            cmd = ["am", "start", "-a", "android.intent.action.VIEW", "-d", url]
            if package:
                cmd += ["-p", package]
        else:
            package = _android_find_package(key)
            if package:
                cmd = ["monkey", "-p", package, "-c",
                       "android.intent.category.LAUNCHER", "1"]
            else:
                return (f"Could not find an installed app matching '{app_name}'. "
                        f"Make sure it's installed on your device.")
    else:
        # Linux
        binary = _linux_find_binary(key)
        if not binary:
            return (f"Could not find an app matching '{app_name}' on this system. "
                    f"Try installing it or using its exact binary name.")
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



def handle_phone(phone_number: str) -> str:
    """Dial a phone number."""
    # Clean the number
    cleaned = "".join(c for c in phone_number if c.isdigit() or c == "+")
    if not cleaned:
        return f"Invalid phone number: '{phone_number}'"

    if ON_ANDROID:
        # Use Termux:API to open the dialer (safe — doesn't auto-call)
        cmd = ["termux-telephony-call", cleaned]
    else:
        # On Linux, just show what would happen
        return f"[Linux] Would dial {cleaned}. This only works on Android/Termux."

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return f"Dialing {cleaned}..."
        else:
            return f"Failed to dial: {result.stderr.strip()}"
    except FileNotFoundError:
        return "termux-telephony-call not found. Install Termux:API: pkg install termux-api"
    except Exception as e:
        return f"Error dialing: {e}"


def handle_run_command(command: str) -> str:
    """Execute a shell command and return the output."""
    try:
        # Run the command with a timeout to prevent hanging
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
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


# ─── Tool definitions (Ollama format) ────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an application on the device, optionally loading a specific URL in it (for browsers). Use this when the user wants to launch an app or open a website in a specific browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "The name of the application to open (e.g. 'brave', 'chrome', 'firefox', 'camera', 'whatsapp', 'spotify')",
                    },
                    "url": {
                        "type": "string",
                        "description": "Optional URL to open inside the app (e.g. 'https://web.whatsapp.com'). Only use for browsers.",
                    },
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "phone",
            "description": "Make a phone call to a given number. Use this when the user wants to call or dial someone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "The phone number to dial (e.g. '+919876543210', '1234567890')",
                    }
                },
                "required": ["phone_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": "Execute a terminal/shell command on the user's device and return its output. Use this to check system status, list files, run scripts, or act as a terminal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact shell command to execute (e.g. 'ls -la', 'uname -a', 'ping google.com')",
                    }
                },
                "required": ["command"],
            },
        },
    },
]

# Dispatch map
# We use .get() here to ignore extra hallucinated parameters from small models
TOOL_HANDLERS = {
    "open_app": lambda args: handle_open_app(args.get("app_name", ""), args.get("url", "")),
    "phone":    lambda args: handle_phone(args.get("phone_number", "")),
    "run_terminal_command": lambda args: handle_run_command(args.get("command", "")),
}


# ─── Main AI loop ────────────────────────────────────────────────────────────

def run_assistant():
    """Main input → LLM → tool-execution loop."""
    print("═" * 44)
    print("  ⚡ KIRN — Your Offline AI Agent")
    print(f"  Model : {MODEL}")
    print(f"  Device: {'Android/Termux' if ON_ANDROID else 'Linux'}")
    print("  Type 'quit' or 'exit' to stop.")
    print("═" * 44)
    print()

    # Conversation history
    messages: list[dict] = []

    while True:
        # --- Get user input ---
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye! 👋")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print("Bye! 👋")
            break

        messages.append({"role": "user", "content": user_input})

        # Check if this looks like a conversational message that shouldn't trigger tools
        _conversational_triggers = (
            "hi", "hello", "hey", "howdy", "yo", "sup",
            "thanks", "thank you", "bye", "good morning", "good evening",
        )
        _is_conversational = (
            user_input.lower().strip() in _conversational_triggers
            or all(word in _conversational_triggers for word in user_input.lower().split())
        )

        # --- Send to LLM ---
        import time
        start_time = time.time()
        try:
            response = ollama.chat(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                tools=TOOLS,
            )
        except ollama.ResponseError as e:
            print(f"\n❌ Ollama error: {e}")
            print(f"   Is Ollama running? Try: ollama serve")
            print(f"   Is the model pulled? Try: ollama pull {MODEL}\n")
            messages.pop()  # Remove failed message
            continue
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}\n")
            messages.pop()
            continue

        end_time = time.time()
        elapsed_time = end_time - start_time

        assistant_message = response["message"]
        messages.append(assistant_message)

        # --- Handle tool calls ---
        if assistant_message.get("tool_calls") and not _is_conversational:
            for tool_call in assistant_message["tool_calls"]:
                func_name = tool_call["function"]["name"]
                func_args = tool_call["function"]["arguments"]

                print(f"\n⚙️  Calling tool: {func_name}({json.dumps(func_args)})")

                handler = TOOL_HANDLERS.get(func_name)
                if handler:
                    result = handler(func_args)
                else:
                    result = f"Unknown tool: {func_name}"

                print(f"   → {result}")

                # Feed tool result back to the LLM
                messages.append({
                    "role": "tool",
                    "content": result,
                })

            # Get the LLM's final response after tool execution
            try:
                start_time_followup = time.time()
                followup = ollama.chat(
                    model=MODEL,
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                    tools=TOOLS,
                )
                elapsed_time_followup = time.time() - start_time_followup
                followup_msg = followup["message"]
                messages.append(followup_msg)
                if followup_msg.get("content"):
                    print(f"\n🤖 {followup_msg['content']}")
                    print(f"   [⏱️  Initial: {elapsed_time:.2f}s | Follow-up: {elapsed_time_followup:.2f}s]\n")
            except Exception:
                pass  # Non-critical, tool already executed

        # --- Handle text response ---
        elif assistant_message.get("content"):
            print(f"\n🤖 {assistant_message['content']}")
            print(f"   [⏱️  Response time: {elapsed_time:.2f}s]\n")

        else:
            print(f"\n🤖 (no response) [⏱️  {elapsed_time:.2f}s]\n")


if __name__ == "__main__":
    run_assistant()
