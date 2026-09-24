#!/usr/bin/env python3
"""
Chaos Driver — autonomous code evolution toward destruction symphony.

Every cycle:
  1. Read cosmic state + recent telemetry
  2. Ask aichat for a code change
  3. Apply to a git branch
  4. Test the change
  5. Keep if entropy up, rollback otherwise

Logs everything to chaos_log.jsonl.
"""
import json, os, sys, time, subprocess, shutil, re
from datetime import datetime
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from cosmic_data import snapshot as cosmic_snapshot

LOG = Path("chaos_log.jsonl")
BACKUP = Path("dialogue_engine.py.bak")
TARGET = Path("dialogue_engine.py")
CYCLE_SEC = 600              # 10 minutes per attempt
MIN_ENTROPY_GAIN = 0.02      # must improve by this much to keep

def log(rec):
    rec["ts"] = time.time()
    rec["time"] = datetime.now().isoformat()
    with open(LOG, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {rec.get('event')}",
          file=sys.stderr, flush=True)

def recent_entropy(n=100):
    """Return mean entropy from the newest session's last N turns."""
    import glob
    files = sorted(glob.glob("telemetry/session_*_dialogue.jsonl"),
                   key=os.path.getmtime)
    if not files:
        return None
    ents = []
    with open(files[-1], encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("type") == "state" and "entropy" in r:
                ents.append(r["entropy"])
    if not ents:
        return None
    return float(np.mean(ents[-n:]))

def test_engine():
    """Run the engine for 6 seconds. Return (ok, entropy)."""
    try:
        proc = subprocess.Popen(
            ["python", "-u", "dialogue_engine.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(6)
        proc.terminate()
        proc.wait(timeout=3)
    except Exception as e:
        return False, None
    ent = recent_entropy(100)
    return ent is not None, ent

def git(cmd, check=False):
    r = subprocess.run(f"git {cmd}", shell=True, capture_output=True,
                       text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {cmd} failed: {r.stderr}")
    return r.stdout.strip()

def git_dirty():
    return bool(git("status --porcelain").strip())

def ask_ai(cosmic, entropy, recent_code):
    prompt = f"""You are evolving a Python audio engine that generates Arabic phoneme noise.

Current state:
- Kp index: {cosmic.get('kp_value')}
- Schumann: {cosmic.get('schumann_score')}
- Solar wind: {cosmic.get('wind_speed')} km/s
- Current spectral entropy: {entropy:.3f} (max ~14)

Goal: increase chaos to approach a "destruction symphony" — maximum spectral density,
maximum unpredictability, maximum harshness.

Here is the current dialogue_engine.py (relevant section):
---
{recent_code}
---

Suggest ONE specific code change. Format:
FIND: <exact text to find>
REPLACE: <exact text to replace with>
REASON: <one sentence>

The change must:
- Be small (under 10 lines)
- Keep the file syntactically valid Python
- Make the sound harsher/more chaotic
- Not touch file I/O, main(), or imports

Respond only with those three lines. No other text."""

    try:
        r = subprocess.run(
            ["aichat", "-m", "groq:openai/gpt-oss-20b"],
            input=prompt, capture_output=True, text=True, timeout=120,
        )
        return (r.stdout or "").strip()
    except Exception as e:
        return f"ERROR: {e}"

def extract_change(response):
    """Parse FIND/REPLACE/REASON from the response."""
    lines = response.splitlines()
    find_lines = []
    replace_lines = []
    reason = ""
    mode = None
    for line in lines:
        if line.startswith("FIND:"):
            mode = "find"
            find_lines.append(line[5:].strip())
        elif line.startswith("REPLACE:"):
            mode = "replace"
            replace_lines.append(line[8:].strip())
        elif line.startswith("REASON:"):
            reason = line[7:].strip()
            mode = None
        elif mode == "find":
            find_lines.append(line)
        elif mode == "replace":
            replace_lines.append(line)
    return "\n".join(find_lines).strip(), "\n".join(replace_lines).strip(), reason

def apply_change(find, replace):
    """Apply the change and return True on success."""
    s = TARGET.read_text()
    if find not in s:
        return False
    TARGET.write_text(s.replace(find, replace, 1))
    return True

def revert():
    if BACKUP.exists():
        shutil.copyfile(BACKUP, TARGET)

def main():
    print(">> Chaos Driver online.", file=sys.stderr, flush=True)
    while True:
        try:
            # --- READ COSMIC STATE ---
            cosmic = cosmic_snapshot()
            entropy_before = recent_entropy(100)
            if entropy_before is None:
                log({"event": "skip", "reason": "no telemetry yet"})
                time.sleep(CYCLE_SEC)
                continue

            # --- BACKUP ---
            shutil.copyfile(TARGET, BACKUP)

            # --- GET CURRENT CODE SLICE ---
            src = TARGET.read_text()
            slice_ = src[:4000]  # first 4000 chars is enough context

            # --- ASK AI ---
            log({"event": "ask", "kp": cosmic.get("kp_value"),
                 "entropy_before": entropy_before})
            response = ask_ai(cosmic, entropy_before, slice_)
            find, replace, reason = extract_change(response)
            if not find or not replace:
                log({"event": "rejected", "reason": "no parseable change",
                     "response": response[:300]})
                revert()
                time.sleep(CYCLE_SEC)
                continue

            # --- APPLY ---
            if not apply_change(find, replace):
                log({"event": "rejected", "reason": "find string not in file",
                     "find": find[:200]})
                revert()
                time.sleep(CYCLE_SEC)
                continue

            # --- TEST ---
            ok, entropy_after = test_engine()
            gain = (entropy_after - entropy_before) if (ok and entropy_after) else None

            if not ok:
                log({"event": "rollback", "reason": "engine crashed",
                     "reason_text": reason})
                revert()
            elif gain is None or gain < MIN_ENTROPY_GAIN:
                log({"event": "rollback", "reason": "no entropy gain",
                     "entropy_before": entropy_before,
                     "entropy_after": entropy_after,
                     "gain": gain,
                     "reason_text": reason})
                revert()
            else:
                # --- COMMIT ---
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                git("add dialogue_engine.py")
                commit_msg = f"chaos: {reason[:70]} (gain +{gain:.3f})"
                git(f'commit -m "{commit_msg}"')
                log({"event": "accepted", "gain": gain,
                     "entropy_before": entropy_before,
                     "entropy_after": entropy_after,
                     "reason_text": reason,
                     "commit_msg": commit_msg})
                # restart the audio session so it picks up the new code
                subprocess.run("tmux kill-session -t listen 2>/dev/null",
                               shell=True)
                time.sleep(2)
                subprocess.run(
                    "tmux new-session -d -s listen 'python -u dialogue_engine.py | "
                    "mpv --no-video --really-quiet --no-terminal "
                    "--demuxer=rawaudio --demuxer-rawaudio-rate=44100 "
                    "--demuxer-rawaudio-channels=2 --demuxer-rawaudio-format=s16le "
                    "--volume=200 --volume-max=200 -'",
                    shell=True,
                )
        except Exception as e:
            log({"event": "error", "error": str(e)})
            revert()

        time.sleep(CYCLE_SEC)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n>> Chaos Driver stopped.", file=sys.stderr)
