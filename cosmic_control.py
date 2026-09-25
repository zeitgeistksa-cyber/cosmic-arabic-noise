import argparse, json, os, time
from pythonosc.dispatcher import Dispatcher
from pythonosc.udp_server import ThreadingOSCUDPServer

STATE = "/tmp/cosmic_state.json"

DEFAULTS = {
    "master":      0.8,
    "step_scale":  0.35,
    "weights":     [1.0, 0.7, 0.5, 0.4, 0.3, 0.2],
    "lfo_rate":    0.07,
    "drift_rate":  0.03,
    "sub_gain":    0.6,
    "whine_gain":  0.07,
    "sizzle_gain": 0.09,
    "shep_gain":   0.06,
    "frozen":      False,   # freeze learned mutation
    "panic":       False,   # silence
}

def save(state):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE)

def load():
    if not os.path.exists(STATE):
        return dict(DEFAULTS)
    try:
        with open(STATE) as f:
            s = json.load(f)
        return {**DEFAULTS, **s}
    except Exception:
        return dict(DEFAULTS)

# ---- handlers ----
def h_master(addr, *args):
    s = load(); s["master"] = float(args[0]); save(s)

def h_step(addr, *args):
    s = load(); s["step_scale"] = float(args[0]); save(s)

def h_weight(addr, *args):
    # /cosmic/weight <index> <value>
    i, v = int(args[0]), float(args[1])
    s = load()
    if 0 <= i < len(s["weights"]):
        s["weights"][i] = v; save(s)

def h_weights(addr, *args):
    s = load(); s["weights"] = [float(x) for x in args]; save(s)

def h_lfo(addr, *args):   s = load(); s["lfo_rate"]   = float(args[0]); save(s)
def h_drift(addr, *args): s = load(); s["drift_rate"] = float(args[0]); save(s)
def h_sub(addr, *args):   s = load(); s["sub_gain"]   = float(args[0]); save(s)
def h_whine(addr, *args): s = load(); s["whine_gain"] = float(args[0]); save(s)
def h_sizzle(addr, *args):s = load(); s["sizzle_gain"]= float(args[0]); save(s)
def h_shep(addr, *args):  s = load(); s["shep_gain"]  = float(args[0]); save(s)
def h_freeze(addr, *args):s = load(); s["frozen"] = bool(int(args[0])); save(s)
def h_panic(addr, *args): s = load(); s["panic"]  = bool(int(args[0])); save(s)

def h_reset(addr, *args):
    save(dict(DEFAULTS))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ip",   default="127.0.0.1")
    p.add_argument("--port", type=int, default=9000)
    args = p.parse_args()

    if not os.path.exists(STATE):
        save(dict(DEFAULTS))
        print(f"[control] initialized {STATE}")

    d = Dispatcher()
    d.map("/cosmic/master",    h_master)
    d.map("/cosmic/step",      h_step)
    d.map("/cosmic/weight",    h_weight)
    d.map("/cosmic/weights",   h_weights)
    d.map("/cosmic/lfo_rate",  h_lfo)
    d.map("/cosmic/drift_rate",h_drift)
    d.map("/cosmic/sub_gain",  h_sub)
    d.map("/cosmic/whine_gain",h_whine)
    d.map("/cosmic/sizzle_gain",h_sizzle)
    d.map("/cosmic/shep_gain", h_shep)
    d.map("/cosmic/freeze",    h_freeze)
    d.map("/cosmic/panic",     h_panic)
    d.map("/cosmic/reset",     h_reset)

    srv = ThreadingOSCUDPServer((args.ip, args.port), d)
    print(f"[control] listening on {args.ip}:{args.port}")
    print("[control] examples:")
    print("  /cosmic/master 0.6")
    print("  /cosmic/weight 3 0.9")
    print("  /cosmic/freeze 1")
    srv.serve_forever()

if __name__ == "__main__":
    main()
