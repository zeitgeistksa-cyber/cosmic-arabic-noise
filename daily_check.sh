#!/data/data/com.termux/files/usr/bin/bash
cd ~/cosmic_arabic_noise
python read_timeline.py > experiments/daily_$(date +%Y%m%d).txt
python << 'PYEOF'
import json
entries = [json.loads(l) for l in open("experiments/timeline.jsonl") if l.strip()]
kps = [e["cosmic"]["kp"] for e in entries if e["cosmic"].get("kp")]
print(f"Windows: {len(entries)}  Kp range: {min(kps)} - {max(kps)}")
if max(kps) - min(kps) > 0.5:
    print(">> COSMIC EVENT DETECTED — inspect findings")
else:
    print(">> still flat")
PYEOF
