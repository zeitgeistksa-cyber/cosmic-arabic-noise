#!/data/data/com.termux/files/usr/bin/bash
# Launch a tmux dashboard with live panes for the whole system.
cd "$(dirname "$0")"

SESSION="cosmic"

# Kill any existing session with the same name
tmux kill-session -t "$SESSION" 2>/dev/null

# Create the session with pane 0: engine
tmux new-session -d -s "$SESSION" -n "main"
tmux send-keys -t "$SESSION:0.0" "cd $(pwd) && ./start.sh" C-m

# Split horizontally: pane 1 = root watcher
tmux split-window -h -t "$SESSION:0.0"
tmux send-keys -t "$SESSION:0.1" "cd $(pwd) && sleep 2 && python watch_roots.py" C-m

# Split pane 1 vertically: pane 2 = entropy watcher
tmux split-window -v -t "$SESSION:0.1"
tmux send-keys -t "$SESSION:0.2" "cd $(pwd) && sleep 3 && python watch_entropy.py" C-m

# Split pane 0 vertically: pane 3 = cosmic data
tmux split-window -v -t "$SESSION:0.0"
tmux send-keys -t "$SESSION:0.3" "cd $(pwd) && while true; do clear; python cosmic_data.py; sleep 60; done" C-m

# New window for autonomous dev loop
tmux new-window -t "$SESSION" -n "ai"
tmux send-keys -t "$SESSION:ai.0" "cd $(pwd) && python autonomous_dev.py" C-m

# New window for GitHub status
tmux new-window -t "$SESSION" -n "git"
tmux send-keys -t "$SESSION:git.0" "cd $(pwd) && while true; do clear; git log --oneline -10; echo; git status -s; sleep 30; done" C-m

# Attach
tmux attach -t "$SESSION"
