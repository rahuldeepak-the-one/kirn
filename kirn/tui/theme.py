"""kirn/tui/theme.py — Kirn custom theme: colors, banner, and styled output."""

# ─── ANSI 256-color helpers ───────────────────────────────────────────────────
# Using raw ANSI escape codes for full terminal compatibility (no dependency).

_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_ITALIC = "\033[3m"

# ─── Kirn Color Palette ──────────────────────────────────────────────────────
# Inspired by cyberpunk neon: cool cyan, violet accents, warm amber warnings

class C:
    """Kirn colour constants — ANSI 256-color / truecolor escape sequences."""
    # Core
    CYAN      = "\033[38;2;0;215;255m"     # #00d7ff — primary brand
    VIOLET    = "\033[38;2;189;147;249m"    # #bd93f9 — accent
    MINT      = "\033[38;2;80;250;123m"     # #50fa7b — success / AI reply
    AMBER     = "\033[38;2;255;183;77m"     # #ffb74d — warning / timing
    RED       = "\033[38;2;255;85;85m"      # #ff5555 — error
    PINK      = "\033[38;2;255;121;198m"    # #ff79c6 — tool calls
    GREY      = "\033[38;2;108;108;108m"    # #6c6c6c — dimmed text
    WHITE     = "\033[38;2;248;248;242m"    # #f8f8f2 — normal text
    BLUE      = "\033[38;2;98;114;164m"     # #6272a4 — subtle
    ORANGE    = "\033[38;2;255;184;108m"    # #ffb86c — accents

    # Background
    BG_DARK   = "\033[48;2;30;30;46m"      # #1e1e2e — dark bg
    BG_LINE   = "\033[48;2;40;42;54m"      # #282a36 — highlight bg


# ─── Styled output functions ─────────────────────────────────────────────────

def banner(model: str, device: str) -> str:
    """Return the Kirn startup banner string."""
    bar = f"{C.CYAN}{_BOLD}{'━' * 50}{_RESET}"
    return f"""
{bar}
{C.CYAN}{_BOLD}  ⚡ K I R N{_RESET}{C.GREY}  ·  AI-Integrated Terminal{_RESET}
{bar}
{C.GREY}  model  {_RESET}{C.WHITE}{model}{_RESET}
{C.GREY}  device {_RESET}{C.WHITE}{device}{_RESET}
{C.GREY}  ─────────────────────────────────────{_RESET}
{C.VIOLET}  ?{C.GREY} <question>     {C.WHITE}ask AI{_RESET}
{C.PINK}  open{C.GREY}/<{C.PINK}call{C.GREY}> <x>  {C.WHITE}AI action{_RESET}
{C.CYAN}  <command>        {C.WHITE}real shell{_RESET}
{C.AMBER}  Ctrl+C{C.GREY} / {C.AMBER}exit   {C.WHITE}quit{_RESET}
{bar}
"""


def ai_reply(text: str) -> str:
    """Format an AI response."""
    return f"\n{C.MINT}{_BOLD}🤖 {_RESET}{C.WHITE}{text}{_RESET}"


def ai_timing(seconds: float) -> str:
    """Format a timing badge."""
    return f"{C.GREY}   ⏱️  {seconds:.2f}s{_RESET}\n"


def ai_timing_dual(initial: float, followup: float) -> str:
    """Format dual timing (initial + follow-up)."""
    return f"{C.GREY}   ⏱️  initial {initial:.2f}s · follow-up {followup:.2f}s{_RESET}\n"


def tool_call(name: str, args_json: str) -> str:
    """Format a tool call."""
    return f"\n{C.PINK}{_BOLD}⚙️  {name}{_RESET}{C.GREY}({args_json}){_RESET}"


def tool_result(text: str) -> str:
    """Format a tool result."""
    return f"{C.CYAN}   → {text}{_RESET}"


def error(text: str) -> str:
    """Format an error message."""
    return f"\n{C.RED}{_BOLD}✗ {text}{_RESET}"


def error_explain_header() -> str:
    """Header shown before AI explains a shell error."""
    return f"\n{C.AMBER}{_BOLD}🤖 Kirn is explaining the error...{_RESET}\n"


def ai_error(text: str) -> str:
    """Format an AI connectivity error."""
    return f"\n{C.RED}{_BOLD}❌ AI error:{_RESET} {C.WHITE}{text}{_RESET}\n"


def dim(text: str) -> str:
    """Dim text for secondary information."""
    return f"{C.GREY}{text}{_RESET}"


def bye() -> str:
    """Exit message."""
    return f"{C.VIOLET}{_BOLD}Bye! 👋{_RESET}"
