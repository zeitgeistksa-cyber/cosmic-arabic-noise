#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
echo "=================================================================="
echo "   ARABIC PHONEME NOISE ENGINE v3.2"
echo "=================================================================="
[ -d brains ] && ls -1 brains/gen_*.npz 2>/dev/null | tail -1 | xargs -I{} echo "Brain: {}"
echo " Ctrl+C to stop. Device volume LOW."
echo "=================================================================="
python arabic_noise_engine.py | mpv --no-video --really-quiet --no-terminal \
    --demuxer=rawaudio --demuxer-rawaudio-rate=44100 \
    --demuxer-rawaudio-channels=2 --demuxer-rawaudio-format=s16le \
    --volume=200 --volume-max=200 - &
PID=$!
trap "echo -e '\n>> Shutting down...'; kill $PID 2>/dev/null; wait $PID 2>/dev/null; exit 0" INT
wait $PID
