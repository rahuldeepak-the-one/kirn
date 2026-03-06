"""kirn/tools/__init__.py — Tool registry: schemas + dispatch.

To add a new tool:
  1. Create kirn/tools/your_tool.py with a handle_xxx() function
  2. Add the Ollama JSON schema to TOOLS below
  3. Add the handler to TOOL_HANDLERS below
"""

import json
from kirn.tools.app import handle_open_app
from kirn.tools.phone import handle_phone
from kirn.tools.terminal import handle_run_command


# ─── Ollama tool schemas ──────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": (
                "Open an application on the device, optionally loading a URL in it. "
                "Use this when the user wants to launch an app or open a website in a browser."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the app to open (e.g. 'brave', 'firefox', 'spotify', 'whatsapp')",
                    },
                    "url": {
                        "type": "string",
                        "description": "Optional URL to open inside a browser (e.g. 'https://web.whatsapp.com')",
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
            "description": "Make a phone call. Use when the user says 'call X' or 'dial X'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "Phone number to dial (e.g. '+919876543210')",
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
            "description": "Run a shell command and return its output. Use when the user provides an explicit command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute (e.g. 'ls -la', 'uname -a')",
                    }
                },
                "required": ["command"],
            },
        },
    },
]

# ─── Dispatch map ──────────────────────────────────────────────────────────────
# .get() used to safely ignore any hallucinated extra params from small models

TOOL_HANDLERS: dict = {
    "open_app":            lambda a: handle_open_app(a.get("app_name", ""), a.get("url", "")),
    "phone":               lambda a: handle_phone(a.get("phone_number", "")),
    "run_terminal_command": lambda a: handle_run_command(a.get("command", "")),
}


def execute_tool(tool_call: dict) -> str:
    """Execute a tool call returned by the LLM and return the result string."""
    func_name = tool_call["function"]["name"]
    func_args = tool_call["function"]["arguments"]
    print(f"\n⚙️  Calling tool: {func_name}({json.dumps(func_args)})")
    handler = TOOL_HANDLERS.get(func_name)
    result = handler(func_args) if handler else f"Unknown tool: {func_name}"
    print(f"   → {result}")
    return result
