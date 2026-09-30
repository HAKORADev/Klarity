#!/usr/bin/env bash
# ============================================================
# Klarity — Install desktop shortcut & shell alias
# ============================================================
set -euo pipefail

# Resolve the directory where this script lives (realpath for symlinks)
INSTALL_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
KLARITY_BIN="$INSTALL_DIR/klarity"
KLARITY_ICON="$INSTALL_DIR/_internal/logo.png"
DESKTOP_FILE="$HOME/.local/share/applications/klarity.desktop"

# --- Pre-flight checks ---
if [[ ! -f "$KLARITY_BIN" ]]; then
    echo "ERROR: klarity binary not found at $KLARITY_BIN"
    exit 1
fi

if [[ ! -f "$KLARITY_ICON" ]]; then
    echo "ERROR: _internal/logo.png not found at $KLARITY_ICON"
    exit 1
fi

if [[ ! -x "$KLARITY_BIN" ]]; then
    echo "Making klarity executable..."
    chmod +x "$KLARITY_BIN"
fi

# --- Create .desktop shortcut ---
echo "Creating desktop shortcut..."
mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Name=Klarity
Comment=Image/Video Restoration Tool
Exec=${KLARITY_BIN}
Icon=${KLARITY_ICON}
Terminal=false
Type=Application
Categories=Graphics;
StartupNotify=true
DESKTOP

chmod 644 "$DESKTOP_FILE"

# Update desktop databases so it appears immediately
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

# --- Detect user's shell and add alias ---
SHELL_NAME=""
SHELL_RC=""

# Check current shell, fall back to common checks
if [[ -n "${ZSH_VERSION:-}" ]] || [[ "$(basename "${SHELL:-}")" == "zsh" ]]; then
    SHELL_NAME="zsh"
    SHELL_RC="$HOME/.zshrc"
elif [[ -n "${BASH_VERSION:-}" ]] || [[ "$(basename "${SHELL:-}")" == "bash" ]]; then
    SHELL_NAME="bash"
    SHELL_RC="$HOME/.bashrc"
fi

# If we still can't tell, check which files exist
if [[ -z "$SHELL_RC" ]]; then
    if [[ -f "$HOME/.zshrc" ]]; then
        SHELL_NAME="zsh"
        SHELL_RC="$HOME/.zshrc"
    elif [[ -f "$HOME/.bashrc" ]]; then
        SHELL_NAME="bash"
        SHELL_RC="$HOME/.bashrc"
    else
        SHELL_NAME="bash"
        SHELL_RC="$HOME/.bashrc"
    fi
fi

ALIAS_MARKER="# >>> Klarity alias >>>"
ALIAS_LINE="alias klarity='${KLARITY_BIN}'"

# Check if alias already exists in that rc file
if [[ -f "$SHELL_RC" ]]; then
    if grep -qF "$ALIAS_MARKER" "$SHELL_RC"; then
        echo "Shell alias already exists in $SHELL_RC (skipping)"
    else
        echo "Adding alias to $SHELL_RC ($SHELL_NAME)..."
        echo "" >> "$SHELL_RC"
        echo "$ALIAS_MARKER" >> "$SHELL_RC"
        echo "$ALIAS_LINE" >> "$SHELL_RC"
        echo "# <<< Klarity alias <<<" >> "$SHELL_RC"
    fi
else
    echo "Creating $SHELL_RC with alias ($SHELL_NAME)..."
    echo "$ALIAS_MARKER" >> "$SHELL_RC"
    echo "$ALIAS_LINE" >> "$SHELL_RC"
    echo "# <<< Klarity alias <<<" >> "$SHELL_RC"
fi

# --- Also handle the other shell if both exist ---
OTHER_RC=""
if [[ "$SHELL_RC" == "$HOME/.bashrc" ]] && [[ -f "$HOME/.zshrc" ]]; then
    OTHER_RC="$HOME/.zshrc"
elif [[ "$SHELL_RC" == "$HOME/.zshrc" ]] && [[ -f "$HOME/.bashrc" ]]; then
    OTHER_RC="$HOME/.bashrc"
fi

if [[ -n "$OTHER_RC" ]]; then
    if grep -qF "$ALIAS_MARKER" "$OTHER_RC"; then
        echo "Alias already exists in $OTHER_RC (skipping)"
    else
        echo "Also adding alias to $OTHER_RC..."
        echo "" >> "$OTHER_RC"
        echo "$ALIAS_MARKER" >> "$OTHER_RC"
        echo "$ALIAS_LINE" >> "$OTHER_RC"
        echo "# <<< Klarity alias <<<" >> "$OTHER_RC"
    fi
fi

# --- Done ---
echo ""
echo "============================================================"
echo " Klarity installed successfully!"
echo "============================================================"
echo ""
echo " Desktop shortcut:  $DESKTOP_FILE"
echo "                     Klarity now appears in your app menu"
echo "                     under Graphics."
echo ""
echo " Shell alias:       $ALIAS_LINE"
echo "                     Open a new terminal or run:"
echo "                       source $SHELL_RC"
echo "                     Then use: klarity info"
echo ""
echo "============================================================"

