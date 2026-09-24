#!/usr/bin/env python3
"""
AI Advisor for the Live Destruction Engine.

Every N seconds:
  1. Read current physics state + params
  2. Ask aichat for parameter tweaks that increase destruction
  3. Validate the response
  4. Write new params (engine picks them up on next poll)
  5. Log everything
"""
import json, subprocess, sys, time
from datetime import datetime
from pathlib import Path
import numpy as np

STATE_FILE = Path("destruction_state.json")
PARAMS_FILE = Path("destruction_params.json")
LOG_FILE = Path("destruction_ai_log.jsonl")

CYCLE_SEC = 120  # 2 minutes between AI consultations

# Parameter bounds — the AI cannot escape these
BOUNDS = {
    "schumann_gain":    (0.05, 0.30),
    "seismic_gain":     (0.10, 0.40),
    "turbulence_gain":  (0.10, 0.40),
    "volcanic_rate":    (0.02, 0.40),
    "flood_gain":       (0.05, 0.30),
    "twin_gain":        (0.10, 0.40),
    "crack_rate":       (0.05, 1.00),
    "swell_depth":      (0.0, 0.8),
    "saturation":       (1.0, 2.5),
    "chaos_rate":       (0.3, 2.5),
    "real_earthquake":  (0.0, 0.60),
    "real_volcano":     (0.0, 0.60),
    "real_storm":       (0.0, 0.50),
    "real_wind":        (0.0, 0.50),
    "real_fire":        (0.0, 0.30),
    "real_wave":        (0.0, 0.50),
    "real_tremor":      (0.0, 0.60),
    "real_explosion":   (0.0, 0.40),
}


def log(rec):
    rec["ts"] = time.time()
    rec["time"] = datetime.now().isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {rec.get('event')}",
          file=sys.stderr, flush=True)


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return None


def load_params():
    if PARAMS_FILE.exists():
        try:
            return json.loads(PARAMS_FILE.read_text())
        except Exception:
            pass
    return None


def clamp_params(p):
    out = {}
    for k, v in p.items():
        if k in BOUNDS:
            lo, hi = BOUNDS[k]
            try:
                out[k] = float(np.clip(float(v), lo, hi))
            except (ValueError, TypeError):
                pass
    return out


def ask_ai(state, params):
    prompt = f"""You are advising a live audio synthesis engine that generates a continuous
"universe cracking" sound. It layers Schumann resonance, earthquake rumble, hurricane
turbulence, volcanic explosions, flood hiss, twin phoneme engines, and cracks.

Current physics state:
- Lorenz attractor: {[round(x, 3) for x in state['lorenz']]}
- Rossler attractor: {[round(x, 3) for x in state['rossler']]}
- Twin engine lock: {state['twin_lock']:.3f} (0 = detuned, 1 = phase-locked)

Current parameters:
{json.dumps(params, indent=2)}

Parameter bounds:
{json.dumps({k: list(v) for k, v in BOUNDS.items()}, indent=2)}

Suggest ONE small change: which parameter to adjust, to what value, and why.
Aim for maximum sonic intensity and continuous evolution toward a "destruction symphony".

Respond with EXACTLY this format on three lines:
PARAM: <parameter_name>
VALUE: <new_numeric_value>
REASON: <one short sentence>"""

    try:
        result = subprocess.run(
            ["aichat", "-m", "groq:openai/gpt-oss-20b"],
            input=prompt, capture_output=True, text=True, timeout=90,
        )
        return (result.stdout or "").strip()
    except Exception as e:
        return f"ERROR: {e}"


def parse_response(text):
    param = None
    value = None
    reason = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("PARAM:"):
            param = line[6:].strip()
        elif line.startswith("VALUE:"):
            try:
                value = float(line[6:].strip())
            except ValueError:
                value = None
        elif line.startswith("REASON:"):
            reason = line[7:].strip()
    return param, value, reason


def main():
    print(">> AI Advisor online", file=sys.stderr, flush=True)
    while True:
        try:
            state = load_state()
            params = load_params()
            if state is None or params is None:
                log({"event": "skip", "reason": "no state yet"})
                time.sleep(CYCLE_SEC)
                continue

            log({"event": "ask",
                 "lorenz_mag": float(np.linalg.norm(state["lorenz"])),
                 "twin_lock": state["twin_lock"]})

            response = ask_ai(state, params)
            param, value, reason = parse_response(response)

            if param is None or value is None or param not in BOUNDS:
                log({"event": "reject", "reason": "unparseable",
                     "response": response[:300]})
                time.sleep(CYCLE_SEC)
                continue

            # Clamp
            lo, hi = BOUNDS[param]
            old = params.get(param)
            new = float(np.clip(value, lo, hi))

            if abs(new - old) < 1e-6:
                log({"event": "reject", "reason": "no change"})
                time.sleep(CYCLE_SEC)
                continue

            params[param] = new
            PARAMS_FILE.write_text(json.dumps(params, indent=2))

            log({"event": "applied",
                 "param": param,
                 "old": old,
                 "new": new,
                 "reason": reason})

        except Exception as e:
            log({"event": "error", "error": str(e)})

        time.sleep(CYCLE_SEC)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n>> Advisor stopped.", file=sys.stderr)
