#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
if [ -t 1 ]; then
    python dialogue_engine.py | mpv --no-video --really-quiet --no-terminal \
        --demuxer=rawaudio --demuxer-rawaudio-rate=44100 \
        --demuxer-rawaudio-channels=2 --demuxer-rawaudio-format=s16le \
        --volume=200 --volume-max=200 -
else
    python dialogue_engine.py > /dev/null
fi
