#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
echo ">> Downloading Quran root vocabulary..."
mkdir -p arabic_db
curl -sL -o arabic_db/quranRoots.json \
  https://raw.githubusercontent.com/AbstractThinker0/quran-roots/master/quranRoots.json
SIZE=$(du -h arabic_db/quranRoots.json | cut -f1)
echo ">> Downloaded ($SIZE)"
echo ">> Extracting triliteral roots..."
python extract_roots.py
echo ""
echo ">> Setup complete. Files:"
wc -l arabic_db/roots.txt 2>/dev/null
echo ""
echo ">> Next: ./start.sh"
