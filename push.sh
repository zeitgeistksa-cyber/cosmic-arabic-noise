#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
MSG="${1:-Auto-commit: $(date +%Y-%m-%d_%H:%M:%S)}"
git add -A
git commit -m "$MSG" || { echo "Nothing to commit"; exit 0; }
git push
echo ">> Pushed: $MSG"
