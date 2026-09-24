#!/usr/bin/env python3
"""
Universe Listener — autonomous cosmic dialogue loop.

Every 30 seconds:
  - Read live cosmic state
  - Read the last 50 engine turns from telemetry
  - Compute the phase-model target CoG and the engine's current CoG
  - Log to knowledge.jsonl

Every 15 minutes:
  - Send the accumulated trend to aichat (Groq) for suggestions
  - Write suggestions to agent/universe_dialogue_NNN.md

Every 5 minutes:
  - If the engine is far off-target for a sustained period,
    write a warning to knowledge.jsonl (but do not modify the engine)
"""
import os, sys, json, time, glob, subprocess
from datetime import datetime
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from cosmic_data import snapshot as cosmic_snapshot
from phase_controller import expected_cog, current_engine_cog, drift

KNOWLEDGE = Path("knowledge.jsonl")
PROPOSALS = Path("agent/universe_dialogue")
PROPOSALS.mkdir(parents=True, exist_ok=True)

POLL_SEC = 30
AI_SEC = 900
DRIFT_WARN = 0.15

def log(record):
    record["ts"] = time.time()
    record["time"] = datetime.now().isoformat()
    with open(KNOWLEDGE, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")

def recent_turns(n=50):
    files = sorted(glob.glob("telemetry/session_*_dialogue.jsonl"),
                   key=os.path.getmtime)
    if not files:
        return []
    turns = []
    with open(files[-1], encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line: continue
            try: r = json.loads(line)
            except: continue
            if r.get("type") == "turn":
                turns.append(r)
    return turns[-n:]

def ask_ai(prompt):
    try:
        result = subprocess.run(
            ["aichat", "-m", "groq:openai/gpt-oss-20b"],
            input=prompt, capture_output=True, text=True, timeout=90,
        )
        out = (result.stdout or "").strip()
        if not out:
            return f"(no output: {result.stderr[:200]})"
        return out
    except Exception as e:
        return f"(ai error: {e})"

def main():
    print(">> Universe Listener online.", file=sys.stderr, flush=True)
    last_ai = 0
    window = []
    while True:
        try:
            # --- LISTEN ---
            cs = cosmic_snapshot()
            kp = cs.get("kp_value")
            sch = cs.get("schumann_score")
            wind = cs.get("wind_speed")
            expected = expected_cog(kp, sch)

            # --- ENGINE STATE ---
            turns = recent_turns(50)
            actual = current_engine_cog(turns)
            d = drift(expected, actual)

            record = {
                "event": "listen",
                "kp": kp, "schumann": sch, "wind": wind,
                "expected_cog": expected,
                "engine_cog": actual,
                "drift": d,
                "n_turns": len(turns),
            }
            log(record)

            # --- STATUS LINE ---
            status = "ok"
            if d is not None and abs(d) > DRIFT_WARN:
                status = "off_target"
            msg = (f"[{datetime.now().strftime('%H:%M:%S')}]  "
                   f"Kp={kp}  Sch={sch}  target={expected:.3f}  "
                   f"engine={actual if actual is None else f'{actual:.3f}'}  "
                   f"drift={d if d is None else f'{d:+.3f}'}  {status}")
            print(msg, file=sys.stderr, flush=True)
            window.append(record)
            if len(window) > 40:
                window.pop(0)

            # --- AI CONSULTATION ---
            now = time.time()
            if now - last_ai > AI_SEC and len(window) >= 10:
                last_ai = now
                summary = {
                    "recent_kp": [r["kp"] for r in window[-10:]],
                    "recent_schumann": [r["schumann"] for r in window[-10:]],
                    "recent_drift": [r["drift"] for r in window[-10:] if r["drift"] is not None],
                    "mean_engine_cog": float(np.mean([r["engine_cog"] for r in window if r["engine_cog"] is not None])) if any(r["engine_cog"] for r in window) else None,
                }
                prompt = (
                    "You are advising an autonomous audio engine that maps "
                    "Arabic phoneme acoustics to live cosmic state. The phase "
                    "diagram from earlier findings: Kp=1.67 Sch=38 -> CoG 0.30; "
                    "Kp>=2.0 -> CoG 0.75. Recent readings: "
                    f"{json.dumps(summary, default=str)}\n\n"
                    "In 4 bullet points: (1) is the engine tracking the target? "
                    "(2) is there a lag? (3) is there a systematic bias? "
                    "(4) one concrete suggestion for the next hour. Be terse."
                )
                response = ask_ai(prompt)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                out = PROPOSALS / f"advice_{stamp}.md"
                out.write_text(
                    f"# Advice {stamp}\n\n"
                    f"## Summary\n```json\n{json.dumps(summary, indent=2, default=str)}\n```\n\n"
                    f"## AI Response\n\n{response}\n",
                    encoding="utf-8",
                )
                print(f">> wrote {out}", file=sys.stderr, flush=True)
                log({"event": "advice", "path": str(out), "summary": summary})

        except Exception as e:
            print(f"!! error: {e}", file=sys.stderr, flush=True)
            log({"event": "error", "error": str(e)})

        time.sleep(POLL_SEC)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n>> Universe Listener stopped.", file=sys.stderr)
