#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"

# Ensure aichat is configured
if ! command -v aichat >/dev/null 2>&1; then
    echo ">> aichat not found. Installing..."
    pkg install -y aichat
fi

# Quick aichat test
if ! aichat "reply: ready" 2>&1 | grep -q ready; then
    echo "!! aichat not working. Checking config..."
    cat ~/.config/aichat/config.yaml 2>/dev/null
    echo ""
    echo "If the model is wrong, edit: ~/.config/aichat/config.yaml"
    exit 1
fi

echo ">> aichat OK"
exec python agent_orchestrator.py "$@"
