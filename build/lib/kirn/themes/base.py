"""kirn/themes/base.py — Base Theme class with styled output methods.

All themes share the same output methods. Only the COLORS dict changes
per theme — this keeps output formatting consistent and makes adding
new themes dead simple (just define colors).
"""

_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_ITALIC = "\033[3m"


def _fg(hex_color: str) -> str:
    """Convert a #RRGGBB hex string to an ANSI truecolor foreground escape."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"\033[38;2;{r};{g};{b}m"


def _bg(hex_color: str) -> str:
    """Convert a #RRGGBB hex string to an ANSI truecolor background escape."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"\033[48;2;{r};{g};{b}m"


VERSION = "0.2.0"


class Theme:
    """
    A Kirn terminal theme. Constructed from a COLORS dict.

    Required keys in COLORS:
      primary, accent, success, warning, error, tool, dim, text, subtle
    Optional keys:
      bg_dark, bg_highlight
    """

    def __init__(self, name: str, colors: dict[str, str], prompt_style: dict[str, str] | None = None):
        self.name = name
        self.colors = colors
        self.prompt_style = prompt_style or {}

        # Pre-compute ANSI escape codes from hex colors
        self.PRIMARY  = _fg(colors["primary"])
        self.ACCENT   = _fg(colors["accent"])
        self.SUCCESS  = _fg(colors["success"])
        self.WARNING  = _fg(colors["warning"])
        self.ERROR    = _fg(colors["error"])
        self.TOOL     = _fg(colors["tool"])
        self.DIM      = _fg(colors["dim"])
        self.TEXT     = _fg(colors["text"])
        self.SUBTLE   = _fg(colors["subtle"])

    # ─── Styled output ────────────────────────────────────────────────────

    def banner(self, model: str, device: str) -> str:
        bar = f"{self.PRIMARY}{_BOLD}{'━' * 52}{_RESET}"
        thin = f"{self.DIM}{'─' * 52}{_RESET}"

        # Change terminal background if theme specifies one
        bg_cmd = ""
        if "bg_dark" in self.colors:
            bg_cmd = f"\033]11;{self.colors['bg_dark']}\007"

        logo = f"""\
{self.PRIMARY}{_BOLD}  ██╗  ██╗ ██╗ ██████╗  ███╗   ██╗{_RESET}
{self.PRIMARY}{_BOLD}  ██║ ██╔╝ ██║ ██╔══██╗ ████╗  ██║{_RESET}
{self.ACCENT}{_BOLD}  █████╔╝  ██║ ██████╔╝ ██╔██╗ ██║{_RESET}
{self.ACCENT}{_BOLD}  ██╔═██╗  ██║ ██╔══██╗ ██║╚██╗██║{_RESET}
{self.PRIMARY}{_BOLD}  ██║  ██╗ ██║ ██║  ██║ ██║ ╚████║{_RESET}
{self.DIM}  ╚═╝  ╚═╝ ╚═╝ ╚═╝  ╚═╝ ╚═╝  ╚═══╝{_RESET}"""

        return f"""{bg_cmd}
{bar}
{logo}
{self.DIM}  v{VERSION}{_RESET}{self.TEXT}  ·  AI-Integrated Terminal{_RESET}
{thin}
{self.DIM}  model   {_RESET}{self.TEXT}{model}{_RESET}
{self.DIM}  device  {_RESET}{self.TEXT}{device}{_RESET}
{self.DIM}  theme   {_RESET}{self.TEXT}{self.name}{_RESET}
{thin}
{self.ACCENT}  ?{self.DIM} question       {self.TEXT}ask AI{_RESET}
{self.SUCCESS}  @kirn{self.DIM} task       {self.TEXT}autonomous execution{_RESET}
{self.WARNING}  command{self.DIM} desc     {self.TEXT}generate a shell command{_RESET}
{self.PRIMARY}  <command>          {self.TEXT}real shell{_RESET}
{self.DIM}  history            {self.TEXT}show command history{_RESET}
{self.ERROR}  Ctrl+C{self.DIM} / {self.ERROR}exit     {self.TEXT}quit{_RESET}
{bar}
"""

    def ai_reply(self, text: str) -> str:
        return f"\n{self.SUCCESS}{_BOLD}⬡ {_RESET}{self.TEXT}{text}{_RESET}"

    def ai_timing(self, seconds: float) -> str:
        return f"{self.DIM}   ⏱️  {seconds:.2f}s{_RESET}\n"

    def ai_timing_dual(self, initial: float, followup: float) -> str:
        return f"{self.DIM}   ⏱️  initial {initial:.2f}s · follow-up {followup:.2f}s{_RESET}\n"

    def tool_call(self, name: str, args_json: str) -> str:
        return f"\n{self.TOOL}{_BOLD}⚙️  {name}{_RESET}{self.DIM}({args_json}){_RESET}"

    def tool_result(self, text: str) -> str:
        return f"{self.PRIMARY}   → {text}{_RESET}"

    def error(self, text: str) -> str:
        return f"\n{self.ERROR}{_BOLD}✗ {text}{_RESET}"

    def error_explain_header(self) -> str:
        return f"\n{self.WARNING}{_BOLD}⬡ Kirn is interpreting the error...{_RESET}\n"

    def ai_error(self, text: str) -> str:
        return f"\n{self.ERROR}{_BOLD}❌ Kirn System Error:{_RESET} {self.TEXT}{text}{_RESET}\n"

    def dim(self, text: str) -> str:
        return f"{self.DIM}{text}{_RESET}"

    def bye(self) -> str:
        return f"{self.ACCENT}{_BOLD}Bye! 👋{_RESET}"

    def session_summary(self, duration_s: float, cmds: int, queries: int, tools: int, errors: int) -> str:
        """Print a styled session stats summary on exit."""
        mins = int(duration_s // 60)
        secs = int(duration_s % 60)
        time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        bar = f"{self.DIM}{'─' * 40}{_RESET}"
        return (
            f"\n{bar}\n"
            f"{self.PRIMARY}{_BOLD}  ⬡ Session Summary{_RESET}\n"
            f"{bar}\n"
            f"{self.DIM}  ⏱️  Duration      {_RESET}{self.TEXT}{time_str}{_RESET}\n"
            f"{self.DIM}  ⌨  Shell cmds    {_RESET}{self.TEXT}{cmds}{_RESET}\n"
            f"{self.DIM}  💬 AI queries    {_RESET}{self.TEXT}{queries}{_RESET}\n"
            f"{self.DIM}  🔧 Tool actions  {_RESET}{self.TEXT}{tools}{_RESET}\n"
            f"{self.DIM}  ⚠️  Errors caught  {_RESET}{self.TEXT}{errors}{_RESET}\n"
            f"{bar}\n"
        )

    def history_entry(self, index: int, entry: str) -> str:
        """Format a single history entry."""
        return f"{self.DIM}  {index:>4}{_RESET}  {self.TEXT}{entry}{_RESET}"
