#!/usr/bin/env bash
# install_desktop.sh — Registers Kirn as a GUI application on Linux so it appears in your launcher.

set -e

echo "⚡ Installing Kirn Desktop Entry..."

# Define paths
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
APP_DIR="$HOME/.local/share/applications"
KIRN_EXEC="$(which kirn)"

if [ -z "$KIRN_EXEC" ]; then
    echo "❌ Error: 'kirn' executable not found in PATH."
    echo "   Please install kirn via pipx (or pip) first."
    exit 1
fi

# 1. Install Icon
mkdir -p "$ICON_DIR"
cp assets/kirn-logo.svg "$ICON_DIR/kirn.svg"
echo "✅ Installed icon to $ICON_DIR/kirn.svg"

# 2. Create Desktop Entry (.desktop file)
mkdir -p "$APP_DIR"
cat <<EOF > "$APP_DIR/kirn.desktop"
[Desktop Entry]
Version=1.0
Name=Kirn
Comment=AI-Integrated Terminal
Exec=$KIRN_EXEC
Icon=kirn
# Setting Terminal=true tells Linux to launch this in your default graphical terminal emulator (e.g. gnome-terminal)
Terminal=true
Type=Application
Categories=Utility;TerminalEmulator;
Keywords=terminal;ai;shell;
EOF

chmod +x "$APP_DIR/kirn.desktop"
echo "✅ Created desktop entry at $APP_DIR/kirn.desktop"

# Refresh desktop database so menus pick it up immediately
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR"
    echo "✅ Refreshed application menus"
fi

echo ""
echo "🎉 Done! You should now be able to search for 'Kirn' in your application launcher."
