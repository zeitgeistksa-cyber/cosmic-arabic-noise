#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
echo "=================================================================="
echo "   DIALOGUE ENGINE v4.0 — Speak With the Universe"
echo "=================================================================="
echo " Each turn the engine:"
echo "   1. Listens to live cosmic data"
echo "   2. Picks the Arabic root whose phonemes match"
echo "   3. Speaks it as structured noise"
echo "   4. Decodes what it just said"
echo " Ctrl+C to stop."
echo "=================================================================="
python dialogue_engine.py | mpv --no-video --really-quiet --no-terminal \
    --demuxer=rawaudio --demuxer-rawaudio-rate=44100 \
    --demuxer-rawaudio-channels=2 --demuxer-rawaudio-format=s16le \
    --volume=200 --volume-max=200 - &
PID=$!
trap "echo -e '\n>> Shutting down...'; kill $PID 2>/dev/null; wait $PID 2>/dev/null; exit 0" INT
wait $PID
