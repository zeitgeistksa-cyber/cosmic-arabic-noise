#!/data/data/com.termux/files/usr/bin/bash
cd ~/cosmic_arabic_noise

while true; do
    echo ">> channel restart $(date)"
    python channel.py | mpv --no-video --really-quiet --no-terminal \
        --demuxer=rawaudio --demuxer-rawaudio-rate=44100 \
        --demuxer-rawaudio-channels=2 --demuxer-rawaudio-format=s16le \
        --volume=200 --volume-max=200 -
    echo ">> channel died, restarting in 5s"
    sleep 5
done
