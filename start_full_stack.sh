#!/data/data/com.termux/files/usr/bin/bash
cd ~/cosmic_arabic_noise

SESSION="live"
tmux kill-session -t "$SESSION" 2>/dev/null
sleep 1

# Create the session with the first pane (engine + audio)
tmux new-session -d -s "$SESSION" -n "main"
tmux send-keys -t "$SESSION:main.0" \
    'cd ~/cosmic_arabic_noise && python -u dialogue_engine.py | mpv --no-video --really-quiet --no-terminal --demuxer=rawaudio --demuxer-rawaudio-rate=44100 --demuxer-rawaudio-channels=2 --demuxer-rawaudio-format=s16le --volume=180 --volume-max=200 -' C-m

# Pane 1: trainer
tmux split-window -h -t "$SESSION:main.0"
tmux send-keys -t "$SESSION:main.1" \
    'cd ~/cosmic_arabic_noise && python -u continuous_trainer.py' C-m

# Pane 2: dashboard
tmux split-window -v -t "$SESSION:main.1"
tmux send-keys -t "$SESSION:main.2" \
    'cd ~/cosmic_arabic_noise && python watch_training.py' C-m

# Pane 3: raw log stream
tmux split-window -v -t "$SESSION:main.0"
tmux send-keys -t "$SESSION:main.3" \
    'cd ~/cosmic_arabic_noise && tail -f training_log.jsonl' C-m

tmux attach -t "$SESSION"
