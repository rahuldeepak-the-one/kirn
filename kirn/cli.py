"""Kirn — entry point."""

import sys

HELP_TEXT = """
╔══════════════════════════════════════════════════════╗
║            ⚡ KIRN — AI-Integrated Terminal           ║
╠══════════════════════════════════════════════════════╣
║  A real shell with an AI assistant built in.         ║
╚══════════════════════════════════════════════════════╝

USAGE
  kirn                      Start the Kirn terminal
  kirn -h                   Show this help

MODES  (Kirn auto-detects which one to use)
  Shell commands            Anything that looks like a real command
                            e.g.  ls -la  |  git status  |  cd ~/projects

  AI Query  (prefix: ?)     Ask a natural-language question
                            e.g.  ? what does chmod 777 do
                                  ? explain this error

  AI Tools                  Natural-language actions
                            e.g.  open brave
                                  open spotify
                                  call 9876543210
                                  launch whatsapp

  Auto Error Explain        When a shell command fails (exit ≠ 0),
                            Kirn automatically asks the AI to explain
                            what went wrong and how to fix it.

BUILT-IN TOOLS
  open_app   <name> [url]   Open any installed app, optionally with a URL
  phone      <number>       Dial a number (Android/Termux only)
  terminal   <command>      Run a shell command via the AI

NAVIGATION
  ↑ / ↓                    Browse command history
  →                        Accept autosuggestion
  Ctrl+C                   Cancel current input
  exit / quit              Exit Kirn

HISTORY
  Saved to ~/.kirn_history  (persists across sessions)

MODEL
  Default: llama3.2:3b      Change in kirn/config.py
"""

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help", "-help", "help"):
        print(HELP_TEXT)
        sys.exit(0)

    from kirn.tui.prompt import run_terminal
    run_terminal()

if __name__ == "__main__":
    main()
