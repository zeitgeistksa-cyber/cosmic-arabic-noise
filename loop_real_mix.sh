#!/data/data/com.termux/files/usr/bin/bash
cd ~/cosmic_arabic_noise

FILE="${1:-real_disasters_mix.wav}"

if [ ! -f "$FILE" ]; then
    echo "!! $FILE not found."
    echo "   Generate it first: python real_only_mix.py"
    exit 1
fi

echo "=================================================================="
echo "  LOOPING: $FILE"
echo "  Ctrl+C to stop."
echo "=================================================================="

while true; do
    mpv --no-video --really-quiet --no-terminal \
        --volume=200 --volume-max=200 \
        "$FILE"
done
