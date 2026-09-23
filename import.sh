#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
[ -z "$1" ] || [ ! -f "$1" ] && { echo "Usage: $0 <archive.tar.gz>"; exit 1; }
TMP=$(mktemp -d); tar -xzf "$1" -C "$TMP"
mkdir -p telemetry brains
for f in "$TMP"/telemetry/session_*.jsonl; do
    [ -e "$f" ] || continue
    cp "$f" "telemetry/imported_$(basename $f)"
    echo "+ telemetry/imported_$(basename $f)"
done
for f in "$TMP"/brains/gen_*.npz; do
    [ -e "$f" ] || continue
    cp "$f" "brains/$(basename ${f%.npz})_imported.npz"
    echo "+ brains/$(basename ${f%.npz})_imported.npz"
done
rm -rf "$TMP"
echo ">> Import done. Run: python train_gen.py"
