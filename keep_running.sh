#!/data/data/com.termux/files/usr/bin/bash
cd ~/cosmic_arabic_noise
while true; do
    echo ">> cycle at $(date +%H:%M:%S)"
    ./run_orchestrator.sh --once
    sleep 300
done
