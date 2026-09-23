#!/usr/bin/env python3
"""
AI Orchestrator
===============
Continuously reads the entire project, briefs Gemini, receives code plans,
writes structured outputs, and shows live activity in the terminal.

Outputs (in agent/):
  context.md       -- what we told Gemini
  plan.md          -- development roadmap Gemini proposed
  tasks.md         -- actionable task list
  suggestions.md   -- code-level suggestions per file
  log.jsonl        -- machine-readable activity log
  history/         -- snapshot of each cycle

Usage:
  python agent_orchestrator.py            # 5-min cycles
  python agent_orchestrator.py --fast     # 2-min cycles
  python agent_orchestrator.py --once     # one pass, exit
"""
import os, sys, json, time, glob, subprocess, re, shutil
from pathlib import Path
from datetime import datetime

CYCLE_DEFAULT = 300
CYCLE_FAST = 120
AGENT_DIR = Path("agent"); AGENT_DIR.mkdir(exist_ok=True)
HISTORY_DIR = AGENT_DIR / "history"; HISTORY_DIR.mkdir(exist_ok=True)
LOG = AGENT_DIR / "log.jsonl"

# ---------- Terminal colors ----------
C = {"reset":"\033[0m","bold":"\033[1m","dim":"\033[2m",
     "blue":"\033[34m","cyan":"\033[36m","green":"\033[32m",
     "yellow":"\033[33m","red":"\033[31m","mag":"\033[35m"}

def banner(title, color="cyan"):
    bar = "═" * 70
    print(f"\n{C[color]}{bar}{C['reset']}")
    print(f"{C[color]}{C['bold']}  {title}{C['reset']}")
    print(f"{C[color]}{bar}{C['reset']}")

def log_event(event, **kwargs):
    rec = {"ts": time.time(), "time": datetime.now().isoformat(),
           "event": event, **kwargs}
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec

# ---------- Project scanner ----------
def scan_project():
    """Read every .py, .sh, .md, .yaml, .json in the project."""
    info = {"files": [], "total_bytes": 0, "by_ext": {}}
    for path in sorted(Path(".").rglob("*")):
        if not path.is_file(): continue
        sp = str(path)
        # Skip noise
        if any(skip in sp for skip in [
            ".git/", "__pycache__/", "telemetry/", "brains/",
            "cosmic_cache/", "arabic_db/quranRoots.json",
            "arabic_db/roots.txt", "logs/", "agent/history/",
            "cosmic_ai_share_", ".venv"]):
            continue
        ext = path.suffix
        size = path.stat().st_size
        info["files"].append({"path": sp, "ext": ext, "size": size})
        info["total_bytes"] += size
        info["by_ext"][ext] = info["by_ext"].get(ext, 0) + 1
    return info

def read_core_sources(max_bytes=8000):
    """Read the important code files, capped per file."""
    core = ["dialogue_engine.py", "phoneme_table.py", "phoneme_grammar.py",
            "root_semantics.py", "cosmic_semantics.py", "cosmic_driver.py",
            "cosmic_data.py", "universal_rhythm.py", "train_gen.py",
            "autonomous_dev.py"]
    out = {}
    for name in core:
        p = Path(name)
        if not p.exists(): continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_bytes:
            text = text[:max_bytes] + "\n... (truncated)\n"
        out[name] = text
    return out

# ---------- Telemetry digest ----------
def telemetry_digest():
    """Summarize the latest dialogue session."""
    files = sorted(glob.glob("telemetry/session_*_dialogue.jsonl"),
                   key=os.path.getmtime)
    if not files:
        return {"turns": 0, "note": "no dialogue log yet"}
    latest = files[-1]
    turns, decodes, roots = [], [], []
    with open(latest, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line: continue
            try: r = json.loads(line)
            except: continue
            if r.get("type") == "turn":
                turns.append(r); roots.append(r.get("root"))
            elif r.get("type") == "decode":
                decodes.append(r)
    from collections import Counter
    c = Counter(roots)
    return {
        "session": os.path.basename(latest),
        "turns": len(turns),
        "decodes": len(decodes),
        "distinct_roots": len(c),
        "top_roots": c.most_common(10),
        "last_cosmic": turns[-1].get("cosmic_raw") if turns else None,
        "last_5_roots": [t["root"] for t in turns[-5:]],
    }

def git_digest():
    """Recent commits + status."""
    def run(cmd):
        try:
            return subprocess.check_output(cmd, shell=True, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:
            return ""
    return {
        "branch": run("git branch --show-current"),
        "recent_commits": run("git log --oneline -8"),
        "status": run("git status -s"),
        "remote": run("git remote -v | head -1"),
    }

def proposals_digest():
    """Latest AI proposals from autonomous_dev.py."""
    props = sorted(glob.glob("proposals/*.md"), key=os.path.getmtime)
    out = []
    for p in props[-3:]:
        try:
            text = Path(p).read_text(encoding="utf-8", errors="replace")
            out.append({"file": os.path.basename(p),
                        "head": text[:600]})
        except Exception:
            pass
    return out

# ---------- Aichat caller ----------
_last_call_ts = [0.0]
_MIN_GAP_SEC = 2.5   # space requests out for free-tier rate limits

def _is_rate_error(text):
    """Detect rate-limit / overload errors from any provider."""
    t = (text or "").lower()
    markers = ["unavailable", "quota", "rate limit", "429", "503",
               "overloaded", "high demand", "try again later"]
    return any(m in t for m in markers)

def ask_gemini(prompt, timeout=120, max_retries=3):
    """Call aichat with retry + rate limiting."""
    import random

    # Global throttle: never fire faster than _MIN_GAP_SEC apart
    gap = time.time() - _last_call_ts[0]
    if gap < _MIN_GAP_SEC:
        time.sleep(_MIN_GAP_SEC - gap)

    backoff = 15  # seconds
    for attempt in range(1, max_retries + 1):
        try:
            _last_call_ts[0] = time.time()
            result = subprocess.run(
                ["aichat", prompt],
                capture_output=True, text=True, timeout=timeout,
            )
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()

            combined = out + " " + err
            if not out and err:
                if _is_rate_error(combined) and attempt < max_retries:
                    wait = backoff + random.randint(0, 5)
                    print(f"    {C['yellow']}[retry {attempt}/{max_retries}] "
                          f"rate-limited, waiting {wait}s{C['reset']}")
                    time.sleep(wait)
                    backoff *= 2
                    continue
                return f"!! aichat error: {err[:300]}"
            return out
        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                print(f"    {C['yellow']}[retry {attempt}/{max_retries}] "
                      f"timeout, retrying...{C['reset']}")
                time.sleep(backoff)
                backoff *= 2
                continue
            return "!! aichat timed out"
        except FileNotFoundError:
            return "!! aichat not found. Run: pkg install aichat"
        except Exception as e:
            return f"!! aichat failed: {e}"
    return "!! aichat exhausted retries"

# ---------- Prompt builders ----------
def build_context(sources, telemetry, git, props, scanner):
    parts = []
    parts.append("# Project Brief\n")
    parts.append("Repository: cosmic-arabic-noise\n")
    parts.append("A self-evolving neural noise engine driven by Arabic "
                 "phoneme acoustics, live cosmic data (Schumann resonance, "
                 "solar wind, Kp index), and the universal 2 Hz communication "
                 "rhythm. The engine speaks Arabic roots as structured noise "
                 "in dialogue with live space-weather data.\n")

    parts.append("## Files\n")
    for f in scanner["files"][:40]:
        parts.append(f"- {f['path']}  ({f['size']}B)")
    parts.append("")

    parts.append("## Source Code\n")
    for name, text in sources.items():
        parts.append(f"### {name}\n```python\n{text}\n```\n")

    parts.append("## Telemetry Digest\n```json\n")
    parts.append(json.dumps(telemetry, indent=2, ensure_ascii=False))
    parts.append("\n```\n")

    parts.append("## Git State\n```\n")
    parts.append(git["recent_commits"] + "\n---\n" + git["status"])
    parts.append("\n```\n")

    if props:
        parts.append("## Recent AI Proposals\n")
        for p in props:
            parts.append(f"### {p['file']}\n{p['head']}\n")

    return "\n".join(parts)

# ---------- Analysis pass ----------
def analyse(cycle, context):
    """Send context to Gemini and collect structured responses."""
    results = {}
    header = (f"[orchestrator] cycle {cycle} — "
              f"{datetime.now().strftime('%H:%M:%S')}")

    # 1) Explain the project back to us
    print(f"{C['blue']}[1/3]{C['reset']} Asking Gemini to explain the project...")
    q1 = (context +
          "\n\n---\n\nTASK 1: In 6 bullet points, explain what this project does "
          "and why it matters. Focus on the sonic / cosmic / Arabic-language "
          "connection. Be concrete. No fluff.")
    results["explain"] = ask_gemini(q1)

    # 2) Development plan
    print(f"{C['blue']}[2/3]{C['reset']} Asking Gemini for a development plan...")
    q2 = (context +
          "\n\n---\n\nTASK 2: Based on everything above, propose a concrete "
          "3-phase development plan for the next month. Phase 1 = quick wins "
          "(under 1 hour each). Phase 2 = medium features (a day each). "
          "Phase 3 = ambitious ideas. Use markdown headers. Be specific about "
          "file names and functions.")
    results["plan"] = ask_gemini(q2)

    # 3) Combined task list + code suggestions (one API call)
    print(f"{C['blue']}[3/3]{C['reset']} Asking Gemini for tasks + code suggestions...")
    q3 = (context +
          "\n\n---\n\nTASK 3: Write a prioritized TODO list. Format each line as: "
          "`[ ] [P0/P1/P2] Short title — one-sentence description`. "
          "Include at least 15 items. Then for the top 3 items only, propose "
          "ONE concrete code change each using:\n"
          "### `filename.py`\n**Why:** one sentence.\n"
          "```python\n<code snippet>\n```\n"
          "Focus on dialogue_engine.py, root_semantics.py, train_gen.py. "
          "Keep changes small and safe.")
    combined = ask_gemini(q3)
    results["tasks"] = combined
    results["suggestions"] = combined

    return results

# ---------- Output writers ----------
def write_outputs(cycle, context, results):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Latest pointers
    (AGENT_DIR / "context.md").write_text(context, encoding="utf-8")
    (AGENT_DIR / "plan.md").write_text(
        f"# Development Plan\n\n_Generated {stamp}_\n\n" +
        results.get("plan", ""), encoding="utf-8")
    (AGENT_DIR / "tasks.md").write_text(
        f"# Task List\n\n_Generated {stamp}_\n\n" +
        results.get("tasks", ""), encoding="utf-8")
    (AGENT_DIR / "suggestions.md").write_text(
        f"# Code Suggestions\n\n_Generated {stamp}_\n\n" +
        results.get("suggestions", ""), encoding="utf-8")
    (AGENT_DIR / "explain.md").write_text(
        f"# Project Explanation\n\n_Generated {stamp}_\n\n" +
        results.get("explain", ""), encoding="utf-8")

    # Snapshot in history/
    snap = HISTORY_DIR / f"cycle_{cycle:04d}_{stamp}.md"
    snap.write_text(
        f"# Cycle {cycle}\n\n## Explain\n{results.get('explain','')}\n\n"
        f"## Plan\n{results.get('plan','')}\n\n"
        f"## Tasks\n{results.get('tasks','')}\n\n"
        f"## Suggestions\n{results.get('suggestions','')}\n",
        encoding="utf-8")
    return snap

# ---------- Printing ----------
def print_digest(name, text, max_lines=30):
    banner(f"GEMINI: {name}", color="green")
    lines = text.splitlines()
    for line in lines[:max_lines]:
        print(f"  {line}")
    if len(lines) > max_lines:
        print(f"  {C['dim']}... ({len(lines)-max_lines} more lines in agent/{name.lower()}.md){C['reset']}")

def print_activity(cycle, telemetry, git, scanner, snap):
    banner(f"CYCLE {cycle} — ACTIVITY SUMMARY", color="mag")
    print(f"  {C['bold']}Files scanned:{C['reset']} {len(scanner['files'])} "
          f"({scanner['total_bytes']//1024} KB total)")
    print(f"  {C['bold']}Telemetry turns:{C['reset']} {telemetry.get('turns',0)}  "
          f"| distinct roots: {telemetry.get('distinct_roots',0)}")
    print(f"  {C['bold']}Git branch:{C['reset']} {git.get('branch','?')}")
    print(f"  {C['bold']}Snapshot:{C['reset']} {snap}")

    print(f"\n  {C['bold']}Top roots the universe asked for:{C['reset']}")
    for root, n in (telemetry.get("top_roots") or [])[:5]:
        bar = "█" * min(n, 40)
        print(f"    {root}  x{n:<3}  {C['cyan']}{bar}{C['reset']}")

    last_cosmic = telemetry.get("last_cosmic")
    if last_cosmic:
        print(f"\n  {C['bold']}Last cosmic state:{C['reset']}")
        for k, v in last_cosmic.items():
            print(f"    {k}: {v}")

# ---------- Main loop ----------
def main():
    fast = "--fast" in sys.argv
    once = "--once" in sys.argv
    cycle_sec = CYCLE_FAST if fast else CYCLE_DEFAULT

    banner("AI ORCHESTRATOR — Gemini Autonomous Development Loop",
           color="yellow")
    print(f"  Cycle time: {cycle_sec}s   Output: agent/")
    print(f"  Log: {LOG}")
    print(f"  Ctrl+C to stop.\n")

    log_event("start", cycle_sec=cycle_sec, fast=fast, once=once)
    cycle = 0
    while True:
        cycle += 1
        started = time.time()

        # ---- Scan ----
        banner(f"CYCLE {cycle} — SCANNING PROJECT", color="cyan")
        scanner = scan_project()
        print(f"  {len(scanner['files'])} files, "
              f"{scanner['total_bytes']//1024} KB")

        sources = read_core_sources()
        print(f"  Loaded {len(sources)} source files for context")
        for name in sources:
            print(f"    {C['dim']}- {name}{C['reset']}")

        telemetry = telemetry_digest()
        print(f"  Telemetry: {telemetry.get('turns',0)} turns, "
              f"{telemetry.get('distinct_roots',0)} distinct roots")

        git = git_digest()
        print(f"  Git: {git.get('branch','?')}  "
              f"{len(git.get('status','').splitlines())} uncommitted")

        props = proposals_digest()
        print(f"  Recent proposals: {len(props)}")

        # ---- Build context ----
        context = build_context(sources, telemetry, git, props, scanner)
        ctx_kb = len(context) / 1024
        print(f"  Context size: {ctx_kb:.1f} KB")

        # ---- Ask Gemini ----
        banner(f"CYCLE {cycle} — CONSULTING GEMINI", color="blue")
        t0 = time.time()
        results = analyse(cycle, context)
        elapsed = time.time() - t0
        print(f"\n  {C['green']}Gemini responded in {elapsed:.1f}s{C['reset']}")

        # ---- Write outputs ----
        snap = write_outputs(cycle, context, results)
        log_event("cycle_complete", cycle=cycle,
                  duration=round(time.time()-started, 1),
                  turns=telemetry.get("turns", 0),
                  context_kb=round(ctx_kb, 1),
                  snapshot=str(snap))

        # ---- Display ----
        print_digest("EXPLAIN", results.get("explain", ""), max_lines=12)
        print_digest("PLAN", results.get("plan", ""), max_lines=20)
        print_digest("TASKS", results.get("tasks", ""), max_lines=25)
        print_digest("SUGGESTIONS", results.get("suggestions", ""), max_lines=20)
        print_activity(cycle, telemetry, git, scanner, snap)

        banner(f"CYCLE {cycle} COMPLETE  ({time.time()-started:.0f}s)",
               color="green")
        print(f"  Read:     agent/explain.md")
        print(f"  Plan:     agent/plan.md")
        print(f"  Tasks:    agent/tasks.md")
        print(f"  Suggest:  agent/suggestions.md")
        print(f"  Snapshot: {snap}")
        print(f"  Log:      {LOG}")

        if once:
            break

        print(f"\n  {C['dim']}Next cycle in {cycle_sec}s — Ctrl+C to stop{C['reset']}")
        try:
            time.sleep(cycle_sec)
        except KeyboardInterrupt:
            break

    log_event("stop", cycles_completed=cycle)
    banner("ORCHESTRATOR STOPPED", color="yellow")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n>> interrupted")
        sys.exit(0)
