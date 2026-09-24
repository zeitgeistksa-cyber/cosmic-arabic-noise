#!/usr/bin/env python3
"""
Destruction Detector — watch for real geomagnetic storms.

Polls Kp every 5 minutes. When Kp crosses a threshold:
  - logs the event to storms.jsonl
  - records 5 minutes of engine output at that moment
  - optionally asks aichat for commentary

Thresholds:
  Kp >= 4  → storm (moderate)
  Kp >= 5  → G1 storm
  Kp >= 7  → G3 storm (destruction-like)
  Kp >= 9  → G5 storm (extreme)

Never modifies the engine. Only observes.
"""
import json, os, sys, time, subprocess
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cosmic_data import snapshot

STORM_LOG = Path("storms.jsonl")
STORM_DIR = Path("storms")
STORM_DIR.mkdir(exist_ok=True)

POLL_SEC = 300
MIN_RECORD_GAP = 3600  # don't re-record within 1 hour

LEVELS = [
    (9.0, "G5"),
    (7.0, "G3"),
    (5.0, "G1"),
    (4.0, "storm"),
    (3.0, "unsettled"),
]

def level_for(kp):
    for threshold, name in LEVELS:
        if kp >= threshold:
            return name
    return "calm"

def log_event(rec):
    rec["ts"] = time.time()
    rec["time"] = datetime.now().isoformat()
    with open(STORM_LOG, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(rec, ensure_ascii=False) + "\n")

def record_audio(duration_sec, label):
    """Capture N seconds of engine output."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw = STORM_DIR / f"{label}_{stamp}.raw"
    try:
        with open(raw, "wb") as fp:
            proc = subprocess.Popen(
                ["python", "-u", "dialogue_engine.py"],
                stdout=fp, stderr=subprocess.DEVNULL,
            )
            time.sleep(duration_sec)
            proc.terminate()
            proc.wait()
        size_mb = raw.stat().st_size / 1e6
        print(f">> recorded {raw} ({size_mb:.1f} MB)", file=sys.stderr)
        return str(raw)
    except Exception as e:
        print(f"!! record failed: {e}", file=sys.stderr)
        return None

def ask_ai(kp, level, sch, wind):
    prompt = (
        f"Live geomagnetic reading: Kp={kp} ({level}), Schumann={sch}, "
        f"solar wind={wind} km/s. "
        "The associated audio engine is at the high-CoG attractor. "
        "In 3 short bullet points: (1) what is happening physically to the "
        "magnetosphere, (2) what the audio character is likely to be, "
        "(3) one physical consequence on Earth's surface. Terse."
    )
    try:
        result = subprocess.run(
            ["aichat", "-m", "groq:openai/gpt-oss-20b"],
            input=prompt, capture_output=True, text=True, timeout=90,
        )
        return (result.stdout or "").strip()
    except Exception as e:
        return f"(ai error: {e})"

def main():
    print(">> Destruction Detector online.", file=sys.stderr, flush=True)
    last_record = 0
    last_level = "calm"

    while True:
        try:
            cs = snapshot()
            kp = cs.get("kp_value")
            sch = cs.get("schumann_score")
            wind = cs.get("wind_speed")
            if kp is None:
                time.sleep(POLL_SEC)
                continue

            level = level_for(kp)
            now = time.time()
            ts = datetime.now().strftime("%H:%M:%S")

            # Detect a level change (upward)
            if level != last_level:
                print(f"[{ts}] Kp={kp} level: {last_level} -> {level}",
                      file=sys.stderr, flush=True)
                log_event({
                    "event": "level_change",
                    "kp": kp, "level": level, "previous": last_level,
                    "schumann": sch, "wind": wind,
                })

                # Record if the event is serious and we haven't just recorded
                if kp >= 4.0 and (now - last_record) > MIN_RECORD_GAP:
                    print(f">> storm detected — recording 5 min of audio",
                          file=sys.stderr, flush=True)
                    path = record_audio(300, level)
                    if path:
                        log_event({
                            "event": "storm_recording",
                            "level": level, "kp": kp, "path": path,
                            "schumann": sch, "wind": wind,
                        })
                        last_record = now

                    # Ask AI for commentary
                    response = ask_ai(kp, level, sch, wind)
                    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    advice = STORM_DIR / f"advice_{stamp}.md"
                    advice.write_text(
                        f"# Storm {stamp}  level={level}  Kp={kp}\n\n"
                        f"## Reading\n```json\n"
                        f"{json.dumps({'kp': kp, 'schumann': sch, 'wind': wind}, indent=2)}\n"
                        f"```\n\n## AI Commentary\n\n{response}\n",
                        encoding="utf-8",
                    )
                    print(f">> wrote {advice}", file=sys.stderr, flush=True)

                last_level = level

            # Heartbeat every 12 polls (~1 hour)
            if int(now) % 3600 < POLL_SEC:
                print(f"[{ts}] heartbeat  Kp={kp}  level={level}",
                      file=sys.stderr, flush=True)

        except Exception as e:
            print(f"!! detector error: {e}", file=sys.stderr, flush=True)

        time.sleep(POLL_SEC)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n>> Detector stopped.", file=sys.stderr)
