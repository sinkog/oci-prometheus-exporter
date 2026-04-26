#!/bin/sh
#
# Initializes the repository by setting up the necessary Git hooks.
# Run once after cloning.
#
# Adapted from: https://github.com/CentralInfraCore/base-repo/tree/main/tools

set -e

GIT_DIR=$(git rev-parse --git-dir)
if [ -z "$GIT_DIR" ]; then
    echo "[ERROR] Not a git repository. Cannot set up hooks."
    exit 1
fi

HOOKS_DIR="$GIT_DIR/hooks"
TOOLS_DIR=$(git rev-parse --show-toplevel)/tools

echo "--- Initializing Git hooks ---"

COMMIT_MSG_HOOK="$HOOKS_DIR/commit-msg"
if [ -f "$COMMIT_MSG_HOOK" ] && [ ! -L "$COMMIT_MSG_HOOK" ]; then
    echo "[INFO] A commit-msg hook already exists. Backing it up to commit-msg.bak."
    mv "$COMMIT_MSG_HOOK" "$COMMIT_MSG_HOOK.bak"
fi

echo "[*] Symlinking commit-msg hook..."
ln -s -f "../../tools/git_hook_commit-msg.sh" "$COMMIT_MSG_HOOK"
echo "  Done."

echo ""
echo "Repository hooks initialized."
echo ""
echo "To sign commits, first start the Vault signing agent:"
echo "  tools/vault-sign-agent.sh -k <key.pem> -c <cert.crt> --root-ca-file <ca.crt>"
