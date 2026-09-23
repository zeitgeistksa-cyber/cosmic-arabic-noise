#!/data/data/com.termux/files/usr/bin/bash
cd ~/cosmic_arabic_noise
while true; do
    python export_snapshot.py
    git add public/snapshot.json
    git commit -m "snapshot: $(date -u +%Y-%m-%dT%H:%M:%SZ)" 2>/dev/null \
        && git push --quiet
    sleep 600
done
