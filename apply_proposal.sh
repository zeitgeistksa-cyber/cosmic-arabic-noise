#!/data/data/com.termux/files/usr/bin/bash

PROPOSAL="$1"

if [ -z "$PROPOSAL" ] || [ ! -f "$PROPOSAL" ]; then
    echo "Usage: $0 <path_to_proposal.md>"
    echo ""
    echo "Available proposals:"
    ls -t proposals_active/*.md 2>/dev/null | head -5
    exit 1
fi

echo ">> Proposal: $PROPOSAL"

PATCH=$(awk '/^```diff/{flag=1;next}/^```/{flag=0}flag' "$PROPOSAL")

if [ -z "$PATCH" ]; then
    echo "!! No diff block found in this proposal"
    echo "   This proposal only contains a description, not a patch."
    exit 1
fi

TMP=$(mktemp /data/data/com.termux/files/home/patch_XXXXXX.patch)
echo "$PATCH" > "$TMP"

echo ">> Patch preview:"
echo "---"
head -30 "$TMP"
echo "---"

read -p "Apply this patch? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ">> Cancelled"
    rm -f "$TMP"
    exit 0
fi

if git apply --check "$TMP" 2>/dev/null; then
    git apply "$TMP"
    git add -u
    git commit -m "AI: $(basename $PROPOSAL .md)"
    echo ">> Applied and committed"
else
    echo "!! Patch did not apply cleanly"
    if git apply --3way "$TMP" 2>/dev/null; then
        git add -u
        git commit -m "AI (3way): $(basename $PROPOSAL .md)"
        echo ">> Applied with 3way and committed"
    else
        echo "!! Failed. Patch saved to: $TMP"
        exit 1
    fi
fi

rm -f "$TMP"
