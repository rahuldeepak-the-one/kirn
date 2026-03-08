# Changelog

All notable changes to Kirn are documented here.

## [0.2.0] — 2026-03-08

### ✨ New Features
- **Autonomous Command Execution** — Kirn can now chain multiple shell commands, interpret errors, and self-correct until a goal is achieved. Prefix with `@kirn` to enter autonomous mode.
- **Command Generation** — Prefix input with `command` (e.g., `command list all docker containers`) to have Kirn generate the right shell command without running it.
- **Git Branch in Prompt** — The terminal prompt now displays the current git branch with a `*` dirty-state indicator when inside a git repository.
- **Rich Prompt** — Shows `user@kirn ~/path  main* ✓ ❯` with exit code tracking (green `✓` or red `✗ code`).
- **Session Statistics** — On exit, Kirn prints a summary: total duration, shell commands run, AI queries, tool actions, and errors caught.
- **Loading Animations** — Contextual spinners while the AI is working:
  - `dots` (⠋⠙⠹⠸) for thinking
  - `moon` (◐◓◑◒) for tool processing
  - `progress` (▰▰▱▱) for command generation
  - `pulse` (○◎●◎) for error interpretation
- **Built-in `history`** — Type `history` to see the last 25 commands, numbered.
- **Built-in `clear`** — Type `clear` to clear the terminal screen natively.
- **Structured Error Analysis** — Failed commands get an AI-generated response in a fixed format: `Summary:` + `Try these commands:`.

### 🎨 UI/UX Improvements
- **ASCII Art Banner** — A custom block-letter KIRN logo with version number and a clean help table.
- **Modern AI Icon** — Replaced the generic robot emoji (🤖) with a sleek hexagonal symbol (⬡).
- **Color-Coded Prompt Elements** — User, host, path, git branch, and exit code each have distinct theme colors.

### 🛠️ Internal Changes
- **CWD-Aware Tool Execution** — `run_terminal_command` now accepts a `cwd` argument, ensuring AI-driven commands run in the correct directory.
- **Iterative Tool Loop** — `_ai_tool` uses a `while` loop (max 10 iterations) to enable multi-step autonomous workflows.
- **JSON Fallback Parser** — Handles edge cases where the LLM outputs raw JSON instead of native tool calls.
- **No Sudo Policy** — System prompt explicitly forbids `sudo` and interactive commands to prevent execution hangs.

## [0.1.0] — 2026-03-03

### Initial Release
- Real shell with bash underneath
- AI inline queries with `?` prefix
- Smart routing: auto-detect command vs. question vs. action
- Auto error explanation on command failure
- Tool calling: `open <app>`, `call <number>`, terminal commands
- Dynamic app discovery
- Tab completion for filesystem paths
- Persistent command history (`~/.kirn_history`)
- Interstellar theme with terminal background color
- Full PTY support for interactive apps (`vim`, `htop`, `ssh`)
- Cross-platform: Linux desktop + Android/Termux
