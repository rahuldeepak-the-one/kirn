"""kirn/themes/interstellar.py — Interstellar theme.

Inspired by deep space: cold stellar blues, warm starlight,
nebula violet, and signal-green readouts against the void.
"""

# ─── Color Palette ────────────────────────────────────────────────────────────
#
#   Think: a spaceship cockpit — cool blue instruments, warm amber readouts,
#   violet nebula glow outside the viewport, green system-OK indicators,
#   and red warning lights.

COLORS = {
    "primary":      "#4fc3f7",    # stellar blue — primary brand / prompt
    "accent":       "#ce93d8",    # nebula violet — ? queries, exit
    "success":      "#a5d6a7",    # signal green — AI replies
    "warning":      "#ffcc80",    # starlight amber — timing, error explain
    "error":        "#ef5350",    # red giant — errors
    "tool":         "#f48fb1",    # pink nebula — tool calls
    "dim":          "#78909c",    # asteroid grey — dimmed text
    "text":         "#eceff1",    # starlight white — normal text
    "subtle":       "#546e7a",    # deep space — subtle elements
    "bg_dark":      "#0a0e17",    # the void — terminal background
}

# ─── prompt_toolkit style overrides ───────────────────────────────────────────
# These are passed to prompt_toolkit's Style.from_dict()

PROMPT_STYLE = {
    "prompt":       "#4fc3f7 bold",
    "path":         "#546e7a",
    "completion-menu":               "bg:#1a237e #eceff1",
    "completion-menu.completion.current": "bg:#283593 #a5d6a7 bold",
}
