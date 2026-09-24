#!/data/data/com.termux/files/usr/bin/bash
cd ~/cosmic_arabic_noise
while true; do
    echo ">> channel restart $(date)"
    python channel.py > /dev/null 2>> channel.err
    echo ">> channel died, restarting in 5s"
    sleep 5
done
