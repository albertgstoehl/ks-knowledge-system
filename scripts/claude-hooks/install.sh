#!/bin/bash
# Install Claude Code Balance hook

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_DIR="$HOME/.claude/hooks"

echo "Installing Balance hook for Claude Code..."

# Create hooks directory
mkdir -p "$HOOK_DIR"

# Create symlink
ln -sf "$SCRIPT_DIR/balance-check.py" "$HOOK_DIR/balance-check.py"

echo "Symlink created: $HOOK_DIR/balance-check.py -> $SCRIPT_DIR/balance-check.py"

# Check if settings.json exists
SETTINGS_FILE="$HOME/.claude/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    echo ""
    echo "Found existing $SETTINGS_FILE"
    echo "Add this to your hooks configuration:"
else
    echo ""
    echo "Create $SETTINGS_FILE with:"
fi

cat << 'EOF'

{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [{
          "type": "command",
          "command": "python3 ~/.claude/hooks/balance-check.py"
        }]
      }
    ]
  }
}
EOF

echo ""
echo "Done! Restart Claude Code to activate."
