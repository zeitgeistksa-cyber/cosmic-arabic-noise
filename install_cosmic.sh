#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "[*] Installing system packages..."
pkg update -y
pkg install -y python mpv ffmpeg

echo "[*] Installing Python deps..."
pip install --quiet --upgrade pip
pip install --quiet numpy scipy

echo "[*] Fetching engine files..."
BASE="https://raw.githubusercontent.com/yourname/cosmic/main"  # <-- replace or drop this block
# If you don't have a repo, comment the curl lines and paste the heredocs instead:
# curl -O $BASE/cosmic_stream.py
# curl -O $BASE/cosmic_telemetry.py
# curl -O $BASE/cosmic_annoyance_v2.py

echo "[*] Writing launcher..."
cat > $PREFIX/bin/cosmic <<'LAUNCH'
#!/data/data/com.termux/files/usr/bin/bash
cd ~/cosmic 2>/dev/null || cd ~
case "$1" in
  live)      python cosmic_stream.py | mpv --no-video \
                --demuxer=rawaudio --demuxer-lavf-format=s16le \
                --demuxer-lavf-o=rate=44100,channels=1 --really-quiet - ;;
  telemetry) python cosmic_telemetry.py ;;
  wav)       python cosmic_annoyance_v2.py && mpv cosmic_annoyance_v2.wav ;;
  *)         echo "usage: cosmic {live|telemetry|wav}" ;;
esac
LAUNCH
chmod +x $PREFIX/bin/cosmic

echo "[*] Done. Try: cosmic live"
