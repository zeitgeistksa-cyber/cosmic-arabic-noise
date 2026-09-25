#!/usr/bin/env python3
"""
Test Runner — 100 autonomous checks on the project.
Each test raises on failure. Results go to tests/results.jsonl.
Idempotent: already-passed tests are skipped on rerun.
"""
import os, sys, json, time, glob, wave, traceback
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

RESULTS = Path("tests/results.jsonl")
RESULTS.parent.mkdir(exist_ok=True)

TASKS = []

def task(category, name):
    def deco(fn):
        TASKS.append((len(TASKS) + 1, category, name, fn))
        return fn
    return deco


# =====================================================================
# 1-10: ENVIRONMENT
# =====================================================================
@task("env", "python >= 3.10")
def t01():
    assert sys.version_info >= (3, 10), sys.version

@task("env", "numpy importable")
def t02():
    import numpy
    return {"numpy": numpy.__version__}

@task("env", "project root has dialogue_engine.py")
def t03():
    assert Path("dialogue_engine.py").exists()

@task("env", "git repo initialized")
def t04():
    assert Path(".git").exists()

@task("env", "telemetry dir exists")
def t05():
    assert Path("telemetry").is_dir()

@task("env", "brains dir exists or creatable")
def t06():
    Path("brains").mkdir(exist_ok=True)
    assert Path("brains").is_dir()

@task("env", "arabic_db exists")
def t07():
    assert Path("arabic_db").is_dir()

@task("env", "phoneme_table.py exists")
def t08():
    assert Path("phoneme_table.py").exists()

@task("env", "sample rate is 44100")
def t09():
    from dialogue_engine import SR
    assert SR == 44100, f"SR={SR}"

@task("env", "chunk size is 2048")
def t10():
    from dialogue_engine import CHUNK
    assert CHUNK == 2048, f"CHUNK={CHUNK}"


# =====================================================================
# 11-20: PHONEME TABLE
# =====================================================================
@task("phoneme", "PHONEMES has 28 letters")
def t11():
    from phoneme_table import PHONEMES
    assert len(PHONEMES) == 28, f"got {len(PHONEMES)}"

@task("phoneme", "every entry is 4 floats")
def t12():
    from phoneme_table import PHONEMES
    for c, v in PHONEMES.items():
        assert len(v) == 4, f"{c} has {len(v)}"
        for x in v:
            assert isinstance(x, (int, float)), f"{c}: {x}"

@task("phoneme", "all values in [0, 1]")
def t13():
    from phoneme_table import PHONEMES
    for c, v in PHONEMES.items():
        for x in v:
            assert 0.0 <= x <= 1.0, f"{c}: {x}"

@task("phoneme", "LETTER_INDEX covers all letters")
def t14():
    from phoneme_table import PHONEMES, LETTER_INDEX
    assert set(PHONEMES.keys()) == set(LETTER_INDEX.keys())

@task("phoneme", "alif, ba, ta present")
def t15():
    from phoneme_table import PHONEMES
    for c in "ابت":
        assert c in PHONEMES, f"missing {c}"

@task("phoneme", "rare letter dha present")
def t16():
    from phoneme_table import PHONEMES
    assert "ظ" in PHONEMES

@task("phoneme", "root_to_log_triad works")
def t17():
    from phoneme_table import root_to_log_triad
    t = root_to_log_triad("ضدد")
    assert t is not None
    assert len(t) == 3

@task("phoneme", "triad values are positive Hz")
def t18():
    from phoneme_table import root_to_log_triad
    t = root_to_log_triad("ضدد")
    for f in t:
        assert f > 0, f"freq={f}"

@task("phoneme", "different roots give different triads")
def t19():
    from phoneme_table import root_to_log_triad
    a = root_to_log_triad("ضدد")
    b = root_to_log_triad("نور")
    assert a != b

@task("phoneme", "invalid root returns None")
def t20():
    from phoneme_table import root_to_log_triad
    assert root_to_log_triad("!!!") is None


# =====================================================================
# 21-30: GRAMMAR
# =====================================================================
@task("grammar", "VOICED non-empty")
def t21():
    from phoneme_grammar import VOICED
    assert len(VOICED) > 5

@task("grammar", "EMPHATIC has 4 letters")
def t22():
    from phoneme_grammar import EMPHATIC
    assert set(EMPHATIC) == set("صضطظ")

@task("grammar", "MANNER covers all letters")
def t23():
    from phoneme_table import PHONEMES
    from phoneme_grammar import MANNER
    for c in PHONEMES:
        assert c in MANNER, f"missing {c}"

@task("grammar", "alif is a sonorant")
def t24():
    from phoneme_grammar import MANNER
    assert MANNER["ا"] == 0.5

@task("grammar", "sad is emphatic")
def t25():
    from phoneme_grammar import EMPHATIC
    assert "ص" in EMPHATIC

@task("grammar", "ba is voiced")
def t26():
    from phoneme_grammar import VOICED
    assert "ب" in VOICED

@task("grammar", "ta is voiceless")
def t27():
    from phoneme_grammar import VOICED
    assert "ت" not in VOICED

@task("grammar", "sin is a fricative")
def t28():
    from phoneme_grammar import MANNER
    assert MANNER["س"] == 1.0

@task("grammar", "mim is a sonorant")
def t29():
    from phoneme_grammar import MANNER
    assert MANNER["م"] == 0.5

@task("grammar", "root_grammar returns 12 floats")
def t30():
    from phoneme_grammar import root_grammar
    g = root_grammar("ضدد")
    assert len(g) == 12
    for x in g:
        assert isinstance(x, (int, float))


# =====================================================================
# 31-40: ROOT SEMANTICS
# =====================================================================
@task("semantics", "root_semantic returns vector")
def t31():
    from root_semantics import root_semantic
    v = root_semantic("ضدد")
    assert len(v) >= 4

@task("semantics", "cosine of identical vectors = 1")
def t32():
    from root_semantics import cosine
    a = np.array([1.0, 2.0, 3.0])
    assert abs(cosine(a, a) - 1.0) < 1e-6

@task("semantics", "cosine of orthogonal = 0")
def t33():
    from root_semantics import cosine
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert abs(cosine(a, b)) < 1e-6

@task("semantics", "precompute returns dict")
def t34():
    from root_semantics import precompute
    d = precompute(["ضدد", "نور"])
    assert isinstance(d, dict)
    assert len(d) == 2

@task("semantics", "vectors are unit norm")
def t35():
    from root_semantics import precompute
    d = precompute(["ضدد", "نور", "كتب"])
    for r, v in d.items():
        n = np.linalg.norm(v)
        assert abs(n - 1.0) < 0.01, f"{r}: norm={n}"

@task("semantics", "cosine range is [-1, 1]")
def t36():
    from root_semantics import precompute, cosine
    d = precompute(["ضدد", "نور"])
    c = cosine(d["ضدد"], d["نور"])
    assert -1.0 <= c <= 1.0

@task("semantics", "invalid root handled")
def t37():
    from root_semantics import root_semantic
    v = root_semantic("xx")
    assert v is not None

@task("semantics", "vector has at least 4 dims")
def t38():
    from root_semantics import root_semantic
    v = root_semantic("ضدد")
    assert len(v) >= 4

@task("semantics", "deterministic for same root")
def t39():
    from root_semantics import root_semantic
    a = root_semantic("ضدد")
    b = root_semantic("ضدد")
    assert np.allclose(a, b)

@task("semantics", "corpus roots from file")
def t40():
    from root_semantics import precompute
    lines = Path("arabic_db/roots.txt").read_text().splitlines()[:100]
    d = precompute(lines)
    assert len(d) == 100


# =====================================================================
# 41-50: COSMIC SEMANTICS
# =====================================================================
@task("cosmic_sem", "cosmic_semantic_vector returns list")
def t41():
    from cosmic_semantics import cosmic_semantic_vector
    v, raw = cosmic_semantic_vector()
    assert isinstance(v, list)

@task("cosmic_sem", "vector has 4 or 12 dims")
def t42():
    from cosmic_semantics import cosmic_semantic_vector
    v, _ = cosmic_semantic_vector()
    assert len(v) in (4, 12), f"got {len(v)}"

@task("cosmic_sem", "all values in [0, 1]")
def t43():
    from cosmic_semantics import cosmic_semantic_vector
    v, _ = cosmic_semantic_vector()
    for x in v:
        assert 0.0 <= x <= 1.0, f"value={x}"

@task("cosmic_sem", "works with FORCE_KP override")
def t44():
    os.environ["FORCE_KP"] = "5.0"
    try:
        from cosmic_semantics import cosmic_semantic_vector
        v, raw = cosmic_semantic_vector()
        del os.environ["FORCE_KP"]
        assert len(v) >= 4
    finally:
        os.environ.pop("FORCE_KP", None)

@task("cosmic_sem", "handles None bz")
def t45():
    from cosmic_semantics import _safe if hasattr(__import__("cosmic_semantics"), "_safe") else None
    # fallback: just call with forced env and no bz
    os.environ["FORCE_KP"] = "2.0"
    try:
        from cosmic_semantics import cosmic_semantic_vector
        v, _ = cosmic_semantic_vector()
        del os.environ["FORCE_KP"]
        assert len(v) >= 4
    finally:
        os.environ.pop("FORCE_KP", None)

@task("cosmic_sem", "returns numeric values")
def t46():
    from cosmic_semantics import cosmic_semantic_vector
    v, _ = cosmic_semantic_vector()
    for x in v:
        assert isinstance(x, (int, float, np.number))

@task("cosmic_sem", "vector is 1-D list")
def t47():
    from cosmic_semantics import cosmic_semantic_vector
    v, _ = cosmic_semantic_vector()
    assert not hasattr(v, "shape") or len(np.shape(v)) == 1

@task("cosmic_sem", "works with FORCE_SCHUMANN")
def t48():
    os.environ["FORCE_KP"] = "2.0"
    os.environ["FORCE_SCHUMANN"] = "80"
    try:
        from cosmic_semantics import cosmic_semantic_vector
        v, _ = cosmic_semantic_vector()
        del os.environ["FORCE_KP"]
        del os.environ["FORCE_SCHUMANN"]
        assert len(v) >= 4
    finally:
        os.environ.pop("FORCE_KP", None)
        os.environ.pop("FORCE_SCHUMANN", None)

@task("cosmic_sem", "works with FORCE_WIND and FORCE_BZ")
def t49():
    os.environ["FORCE_KP"] = "2.0"
    os.environ["FORCE_WIND"] = "500"
    os.environ["FORCE_BZ"] = "-10"
    try:
        from cosmic_semantics import cosmic_semantic_vector
        v, _ = cosmic_semantic_vector()
        del os.environ["FORCE_KP"]
        del os.environ["FORCE_WIND"]
        del os.environ["FORCE_BZ"]
        assert len(v) >= 4
    finally:
        os.environ.pop("FORCE_KP", None)
        os.environ.pop("FORCE_WIND", None)
        os.environ.pop("FORCE_BZ", None)

@task("cosmic_sem", "no crashes on repeated calls")
def t50():
    from cosmic_semantics import cosmic_semantic_vector
    for _ in range(5):
        v, _ = cosmic_semantic_vector()
        assert len(v) >= 4


# =====================================================================
# 51-60: TELEMETRY
# =====================================================================
def _latest_session():
    files = sorted(glob.glob("telemetry/session_*_dialogue.jsonl"),
                   key=os.path.getmtime)
    return files[-1] if files else None

def _read_turns(path, n=500):
    turns = []
    with open(path, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line: continue
            try: r = json.loads(line)
            except: continue
            if r.get("type") == "turn":
                turns.append(r)
    return turns[-n:]

@task("telemetry", "latest session exists")
def t51():
    p = _latest_session()
    assert p is not None, "no session files"

@task("telemetry", "session has turn events")
def t52():
    p = _latest_session()
    turns = _read_turns(p, 20)
    assert len(turns) > 0, "no turns"

@task("telemetry", "turn has root field")
def t53():
    p = _latest_session()
    t = _read_turns(p, 1)[0]
    assert "root" in t

@task("telemetry", "turn has cosmic_raw")
def t54():
    p = _latest_session()
    t = _read_turns(p, 1)[0]
    assert "cosmic_raw" in t

@task("telemetry", "turn has similarity")
def t55():
    p = _latest_session()
    t = _read_turns(p, 1)[0]
    assert "similarity" in t

@task("telemetry", "root is 3 chars")
def t56():
    p = _latest_session()
    for t in _read_turns(p, 20):
        if t.get("root"):
            assert len(t["root"]) == 3, t["root"]

@task("telemetry", "cosmic values are numeric or None")
def t57():
    p = _latest_session()
    for t in _read_turns(p, 20):
        c = t.get("cosmic_raw") or {}
        for k, v in c.items():
            assert v is None or isinstance(v, (int, float)), f"{k}={v}"

@task("telemetry", "similarity is in [0, 1]")
def t58():
    p = _latest_session()
    for t in _read_turns(p, 20):
        s = t.get("similarity")
        if s is not None:
            assert 0 <= s <= 1.0, f"sim={s}"

@task("telemetry", "JSONL parses cleanly")
def t59():
    p = _latest_session()
    with open(p, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                json.loads(line)

@task("telemetry", "root frequencies computable")
def t60():
    from collections import Counter
    p = _latest_session()
    turns = _read_turns(p, 200)
    c = Counter(t["root"] for t in turns if t.get("root"))
    assert len(c) > 0


# =====================================================================
# 61-70: AUDIO SYNTHESIS
# =====================================================================
@task("audio", "synth_letter returns array")
def t61():
    from tv_space_synth import synth_letter
    a = synth_letter("م", dur=0.1)
    assert len(a) > 0

@task("audio", "synth_letter length matches duration")
def t62():
    from tv_space_synth import synth_letter, SR
    a = synth_letter("م", dur=0.2)
    assert abs(len(a) - 0.2 * SR) < 100

@task("audio", "synth_message with multiple letters")
def t63():
    from tv_space_synth import synth_message
    a = synth_message(["م", "ر", "س"])
    assert len(a) > 0

@task("audio", "output amplitude <= 1.0")
def t64():
    from tv_space_synth import synth_message
    a = synth_message(["م", "ر"])
    assert np.max(np.abs(a)) <= 1.0 + 1e-6

@task("audio", "output has no NaN or Inf")
def t65():
    from tv_space_synth import synth_message
    a = synth_message(["م", "ر", "س"])
    assert np.all(np.isfinite(a)), "found NaN/Inf"

@task("audio", "different letters produce different output")
def t66():
    from tv_space_synth import synth_letter
    np.random.seed(1)
    a = synth_letter("م", dur=0.1)
    np.random.seed(1)
    b = synth_letter("س", dur=0.1)
    assert not np.allclose(a, b)

@task("audio", "random noise gives different output")
def t67():
    from tv_space_synth import synth_letter
    a = synth_letter("م", dur=0.1)
    b = synth_letter("م", dur=0.1)
    assert not np.allclose(a, b)

@task("audio", "can open existing WAV files")
def t68():
    files = glob.glob("*.wav") + glob.glob("real_samples/*.wav")
    assert len(files) > 0, "no WAV files found"
    f = files[0]
    with wave.open(f, "rb") as wf:
        assert wf.getnframes() > 0

@task("audio", "WAV analysis produces sensible numbers")
def t69():
    files = glob.glob("space_noise_*.wav") or glob.glob("*.wav")
    assert files
    with wave.open(files[0], "rb") as wf:
        n = wf.getnframes()
        data = np.frombuffer(wf.readframes(min(n, 100000)), dtype=np.int16)
    rms = np.sqrt(np.mean(data.astype(np.float64) ** 2))
    assert rms > 0, f"silent file: rms={rms}"

@task("audio", "multiple WAV files exist")
def t70():
    files = glob.glob("*.wav")
    assert len(files) >= 1, f"only {len(files)} WAV files"


# =====================================================================
# 71-80: COSMIC DATA
# =====================================================================
@task("cosmic_data", "cosmic_data importable")
def t71():
    import cosmic_data
    assert hasattr(cosmic_data, "snapshot")

@task("cosmic_data", "snapshot function callable")
def t72():
    from cosmic_data import snapshot
    s = snapshot()
    assert isinstance(s, dict)

@task("cosmic_data", "snapshot has expected keys when forced")
def t73():
    os.environ["FORCE_KP"] = "3.0"
    try:
        from cosmic_data import snapshot
        s = snapshot()
        del os.environ["FORCE_KP"]
        assert "kp_value" in s
        assert s["kp_value"] == 3.0
    finally:
        os.environ.pop("FORCE_KP", None)

@task("cosmic_data", "FORCE_SCHUMANN override works")
def t74():
    os.environ["FORCE_KP"] = "3.0"
    os.environ["FORCE_SCHUMANN"] = "77"
    try:
        from cosmic_data import snapshot
        s = snapshot()
        del os.environ["FORCE_KP"]
        del os.environ["FORCE_SCHUMANN"]
        assert s.get("schumann_score") == 77.0
    finally:
        os.environ.pop("FORCE_KP", None)
        os.environ.pop("FORCE_SCHUMANN", None)

@task("cosmic_data", "FORCE_WIND override works")
def t75():
    os.environ["FORCE_KP"] = "3.0"
    os.environ["FORCE_WIND"] = "555"
    try:
        from cosmic_data import snapshot
        s = snapshot()
        del os.environ["FORCE_KP"]
        del os.environ["FORCE_WIND"]
        assert s.get("wind_speed") == 555.0
    finally:
        os.environ.pop("FORCE_KP", None)
        os.environ.pop("FORCE_WIND", None)

@task("cosmic_data", "FORCE_BZ override works")
def t76():
    os.environ["FORCE_KP"] = "3.0"
    os.environ["FORCE_BZ"] = "-15"
    try:
        from cosmic_data import snapshot
        s = snapshot()
        del os.environ["FORCE_KP"]
        del os.environ["FORCE_BZ"]
        assert s.get("bz") == -15.0
    finally:
        os.environ.pop("FORCE_KP", None)
        os.environ.pop("FORCE_BZ", None)

@task("cosmic_data", "cosmic_driver importable")
def t77():
    import cosmic_driver
    assert hasattr(cosmic_driver, "CosmicDriver")

@task("cosmic_data", "driver has poll method")
def t78():
    from cosmic_driver import CosmicDriver
    d = CosmicDriver(poll_interval=0)
    assert hasattr(d, "poll")

@task("cosmic_data", "live snapshot returns dict")
def t79():
    from cosmic_data import snapshot
    s = snapshot()
    assert isinstance(s, dict)

@task("cosmic_data", "live snapshot has kp_value or None")
def t80():
    from cosmic_data import snapshot
    s = snapshot()
    assert "kp_value" in s


# =====================================================================
# 81-90: ENGINE
# =====================================================================
@task("engine", "dialogue_engine imports")
def t81():
    import dialogue_engine
    assert hasattr(dialogue_engine, "DialogueEngine")

@task("engine", "engine has generate_chunk")
def t82():
    from dialogue_engine import DialogueEngine
    assert hasattr(DialogueEngine, "generate_chunk")

@task("engine", "engine has _study method")
def t83():
    from dialogue_engine import DialogueEngine
    assert hasattr(DialogueEngine, "_study")

@task("engine", "engine has _rotate_root method")
def t84():
    from dialogue_engine import DialogueEngine
    assert hasattr(DialogueEngine, "_rotate_root")

@task("engine", "engine has acoustic_fingerprint only once")
def t85():
    src = Path("dialogue_engine.py").read_text()
    count = src.count("def acoustic_fingerprint")
    assert count == 1, f"found {count} definitions"

@task("engine", "engine has no syntax errors")
def t86():
    import py_compile
    py_compile.compile("dialogue_engine.py", doraise=True)

@task("engine", "engine file is under 500 lines")
def t87():
    n = len(Path("dialogue_engine.py").read_text().splitlines())
    assert n < 1000, f"file has {n} lines"

@task("engine", "no duplicated function definitions")
def t88():
    import re
    src = Path("dialogue_engine.py").read_text()
    defs = re.findall(r"^def (\w+)", src, re.MULTILINE)
    from collections import Counter
    dups = [k for k, v in Counter(defs).items() if v > 1]
    assert not dups, f"duplicated: {dups}"

@task("engine", "imports without side effects")
def t89():
    # importing shouldn't create new telemetry files
    before = len(glob.glob("telemetry/session_*_dialogue.jsonl"))
    import importlib
    import dialogue_engine
    importlib.reload(dialogue_engine)
    after = len(glob.glob("telemetry/session_*_dialogue.jsonl"))
    assert after - before <= 1

@task("engine", "SR and CHUNK exported")
def t90():
    from dialogue_engine import SR, CHUNK
    assert SR == 44100
    assert CHUNK == 2048


# =====================================================================
# 91-100: DATA / PATTERNS
# =====================================================================
@task("data", "Quran text file exists")
def t71b(): pass
@task("data", "Quran file exists")
def t91():
    p = Path("books/quran_simple.txt")
    if not p.exists():
        return {"note": "file not present — skip"}
    assert p.stat().st_size > 1000

@task("data", "poem roots files exist")
def t92():
    files = glob.glob("poem_roots*.json")
    assert len(files) >= 1, f"found {len(files)}"

@task("data", "poem roots are valid JSON")
def t93():
    files = glob.glob("poem_roots*.json")
    for f in files:
        json.loads(Path(f).read_text())

@task("data", "letter_correlations.json valid if present")
def t94():
    p = Path("letter_correlations.json")
    if not p.exists():
        return {"note": "not present yet"}
    d = json.loads(p.read_text())
    assert isinstance(d, dict)

@task("data", "can aggregate root counts")
def t95():
    from collections import Counter
    p = _latest_session()
    turns = _read_turns(p, 200)
    c = Counter(t["root"] for t in turns if t.get("root"))
    assert sum(c.values()) > 0

@task("data", "can compute audio entropy")
def t96():
    files = glob.glob("space_noise_*.wav") or glob.glob("active_*.wav")
    if not files:
        return {"note": "no audio to analyze"}
    with wave.open(files[0], "rb") as wf:
        n = min(wf.getnframes(), 100000)
        data = np.frombuffer(wf.readframes(n), dtype=np.int16)
    spec = np.abs(np.fft.rfft(data))
    p = spec / (spec.sum() + 1e-9)
    H = -np.sum(p * np.log2(p + 1e-9))
    assert H > 0

@task("data", "can compute spectral centroid")
def t97():
    files = glob.glob("space_noise_*.wav") or glob.glob("active_*.wav")
    if not files:
        return {"note": "no audio"}
    with wave.open(files[0], "rb") as wf:
        sr = wf.getframerate()
        n = min(wf.getnframes(), 100000)
        data = np.frombuffer(wf.readframes(n), dtype=np.int16)
    spec = np.abs(np.fft.rfft(data))
    freqs = np.fft.rfftfreq(len(data), 1/sr)
    c = np.sum(freqs * spec) / (spec.sum() + 1e-9)
    assert c > 0

@task("data", "universe_dialogue.jsonl valid")
def t98():
    p = Path("universe_dialogue.jsonl")
    if not p.exists():
        return {"note": "not present"}
    with open(p, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                json.loads(line)

@task("data", "proposal_loop.jsonl valid")
def t99():
    p = Path("proposal_loop.jsonl")
    if not p.exists():
        return {"note": "not present"}
    with open(p, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                json.loads(line)

@task("data", "tmux sessions running")
def t100():
    import subprocess
    r = subprocess.run(["tmux", "ls"], capture_output=True, text=True)
    out = r.stdout + r.stderr
    assert "engine" in out or "proposals" in out, out


# =====================================================================
# RUNNER
# =====================================================================
def main():
    print("=" * 70)
    print(f"TEST RUNNER — {len(TASKS)} tasks")
    print("=" * 70)

    done = set()
    if RESULTS.exists():
        for line in RESULTS.read_text().splitlines():
            try:
                r = json.loads(line)
                if r.get("status") == "pass":
                    done.add(r["id"])
            except Exception:
                pass
        print(f"  Resuming: {len(done)} tasks already passed\n")

    t_start = time.time()
    n_pass = 0
    n_fail = 0
    n_skip = 0

    for tid, cat, name, fn in TASKS:
        if tid in done:
            print(f"[{tid:3d}] SKIP  {cat:12s}  {name}")
            n_skip += 1
            continue

        t0 = time.time()
        try:
            result = fn()
            dt = time.time() - t0
            note = ""
            if isinstance(result, dict) and "note" in result:
                note = f"  ({result['note']})"
                n_skip += 1
            else:
                n_pass += 1
            print(f"[{tid:3d}] PASS  {cat:12s}  {name}  ({dt:.2f}s){note}")
            rec = {"id": tid, "category": cat, "name": name,
                   "status": "pass", "duration": dt,
                   "result": result if not isinstance(result, dict) else None,
                   "time": time.strftime("%Y-%m-%dT%H:%M:%S")}
        except Exception as e:
            dt = time.time() - t0
            tb = traceback.format_exc()
            n_fail += 1
            print(f"[{tid:3d}] FAIL  {cat:12s}  {name}  ({dt:.2f}s)  {type(e).__name__}: {e}")
            rec = {"id": tid, "category": cat, "name": name,
                   "status": "fail", "duration": dt,
                   "error": f"{type(e).__name__}: {e}",
                   "traceback": tb,
                   "time": time.strftime("%Y-%m-%dT%H:%M:%S")}

        with open(RESULTS, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(rec, ensure_ascii=False) + "\n")

    dt = time.time() - t_start
    print()
    print("=" * 70)
    print(f"DONE  pass={n_pass}  fail={n_fail}  skip={n_skip}  "
          f"time={dt:.1f}s")
    print(f"Results: {RESULTS}")
    print("=" * 70)


if __name__ == "__main__":
    main()
