#!/usr/bin/env bash
# Hermes Vault Plugin — Install / Update Script
# Installs the vault plugin to ~/.hermes/plugins/vault/

set -euo pipefail

PLUGIN_NAME="vault"
TARGET="${HERMES_HOME:-$HOME/.hermes}/plugins/$PLUGIN_NAME"
SOURCE="$(cd "$(dirname "$0")" && pwd)"

echo "  Installing Hermes Vault Plugin..."
echo "  Source: $SOURCE"
echo "  Target: $TARGET"

# Create plugin directory
mkdir -p "$TARGET"

# Copy plugin files
cp "$SOURCE/plugin.yaml" "$TARGET/"
cp "$SOURCE/__init__.py" "$TARGET/"
cp "$SOURCE/vault_crypto.py" "$TARGET/"
cp "$SOURCE/vault_init.py" "$TARGET/"

# Copy dashboard
mkdir -p "$TARGET/dashboard/dist"
cp "$SOURCE/dashboard/manifest.json" "$TARGET/dashboard/"
cp "$SOURCE/dashboard/plugin_api.py" "$TARGET/dashboard/"
cp "$SOURCE/dashboard/dist/index.js" "$TARGET/dashboard/dist/"
cp "$SOURCE/dashboard/dist/style.css" "$TARGET/dashboard/dist/"

# Secure permissions
chmod 700 "$TARGET"
chmod 600 "$TARGET/plugin.yaml"
chmod 644 "$TARGET/__init__.py" "$TARGET/vault_crypto.py" "$TARGET/vault_init.py"
chmod 755 "$TARGET/dashboard"
chmod 644 "$TARGET/dashboard/manifest.json" "$TARGET/dashboard/plugin_api.py"
chmod 755 "$TARGET/dashboard/dist"
chmod 644 "$TARGET/dashboard/dist/index.js" "$TARGET/dashboard/dist/style.css"

echo ""
echo "  ✓ Installed to $TARGET"
echo ""
echo "  Next steps:"
echo "  1. Set up your vault password:"
echo "     python3 $TARGET/vault_init.py"
echo ""
echo "  2. Add to your environment (from the output above)"
echo ""
echo "  3. Enable the plugin:"
echo "     hermes plugins enable vault"
echo ""
echo "  4. Restart the dashboard for the Vault tab:"
echo "     hermes dashboard --force-discover"
echo ""
