#!/data/data/com.termux/files/usr/bin/bash
cd ~/cosmic_arabic_noise

pkill -f live_destruction_real.py 2>/dev/null
pkill -f destruction_ai.py 2>/dev/null
pkill -f mpv 2>/dev/null
sleep 2

# Init params if missing
if [ ! -f destruction_params.json ]; then
    python -c "
from live_destruction_real import DEFAULT_PARAMS
import json
open('destruction_params.json','w').write(json.dumps(DEFAULT_PARAMS, indent=2))
print('>> initialized params')
"
fi

echo ">> Engine starting..."
python -u live_destruction_real.py | mpv --no-video --really-quiet --no-terminal \
    --demuxer=rawaudio --demuxer-rawaudio-rate=44100 \
    --demuxer-rawaudio-channels=2 --demuxer-rawaudio-format=s16le \
    --volume=200 --volume-max=200 - &

ENGINE_PID=$!
sleep 3

echo ">> AI advisor starting..."
python -u destruction_ai.py &
ADVISOR_PID=$!

trap "kill $ENGINE_PID $ADVISOR_PID 2>/dev/null; exit 0" INT
wait
