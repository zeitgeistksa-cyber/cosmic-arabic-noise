#!/data/data/com.termux/files/usr/bin/bash
while true; do
  echo "[*] new solar simulation cycle"
  python solar_acoustic_sim.py 120 | mpv --no-video \
    --demuxer=rawaudio --demuxer-lavf-format=s16le \
    --demuxer-lavf-o=rate=44100,channels=1 \
    --volume=120 --really-quiet -
  echo "[*] cycle complete. checking Gohm logs..."
  ls -t solar_params_gen*.json | head -3
  sleep 5
done
