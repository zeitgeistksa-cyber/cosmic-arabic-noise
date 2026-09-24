#!/data/data/com.termux/files/usr/bin/bash
cd ~/cosmic_arabic_noise

while true; do
    KP=$(python cosmic_data.py | python -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('kp_value') or 0)
")
    echo "Kp = $KP"
    if python -c "exit(0 if float('$KP') < 2.0 else 1)"; then
        echo ">> calm detected — starting 5-minute recording"
        timeout 300 python -u dialogue_engine.py > calm_mode.raw 2>/dev/null
        echo ">> recording complete"
        break
    fi
    sleep 60
done
