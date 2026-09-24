#!/data/data/com.termux/files/usr/bin/bash
cd ~/cosmic_arabic_noise

# Kill stale sessions
pkill -f live_destruction.py 2>/dev/null
pkill -f destruction_ai.py 2>/dev/null
pkill -f mpv 2>/dev/null
sleep 2

# Reset params to defaults
if [ ! -f destruction_params.json ]; then
    python -c "
from live_destruction import DEFAULT_PARAMS
import json
open('destruction_params.json','w').write(json.dumps(DEFAULT_PARAMS, indent=2))
print('>> initialized params')
"
fi

# 1. Start the engine, streaming to mpv
python -u live_destruction.py | mpv --no-video --really-quiet --no-terminal \
    --demuxer=rawaudio --demuxer-rawaudio-rate=44100 \
    --demuxer-rawaudio-channels=2 --demuxer-rawaudio-format=s16le \
    --volume=200 --volume-max=200 - &

ENGINE_PID=$!
echo ">> Engine PID $ENGINE_PID"

# 2. Wait, then start the AI advisor
sleep 3
python -u destruction_ai.py &
ADVISOR_PID=$!
echo ">> Advisor PID $ADVISOR_PID"

# Wait for interrupt
trap "kill $ENGINE_PID $ADVISOR_PID 2>/dev/null; exit 0" INT
wait
