#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
STAMP=$(date +%Y%m%d_%H%M%S)
OUT="cosmic_ai_share_${STAMP}.tar.gz"
python << 'PYEOF'
import json, glob, os, time
from pathlib import Path
m = {"engine": "Arabic Phoneme Noise Engine", "version": "3.2",
     "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
     "telemetry_files": [], "brain_files": [], "total_records": 0}
for f in sorted(glob.glob("telemetry/session_*.jsonl")):
    n = sum(1 for _ in open(f)); m["telemetry_files"].append({"path": f, "records": n}); m["total_records"] += n
for f in sorted(glob.glob("brains/gen_*.npz")):
    m["brain_files"].append({"path": f, "size": os.path.getsize(f)})
Path("manifest.json").write_text(json.dumps(m, indent=2))
print(f">> {len(m['telemetry_files'])} files, {m['total_records']} records, {len(m['brain_files'])} brains")
PYEOF
tar -czf "$OUT" telemetry/ brains/ manifest.json 2>/dev/null
rm -f manifest.json
echo "=================================================================="
echo " SHARE FILE: $OUT  ($(du -h $OUT | cut -f1))"
echo "=================================================================="
echo " Recipient runs: ./import.sh $OUT"
