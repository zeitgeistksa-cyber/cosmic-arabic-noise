import argparse, subprocess, sys, os

def cmd_offline(args):
    from . import offline
    offline.main(args.duration)

def cmd_train(args):
    from . import brain
    brain.train_from(args.log, args.out)

def cmd_live(args):
    from . import stream
    # pipe stdout to mpv
    mpv = subprocess.Popen([
        "mpv", "--no-video",
        "--demuxer=rawaudio", "--demuxer-lavf-format=s16le",
        "--demuxer-lavf-o=rate=44100,channels=1",
        "--really-quiet", "-",
    ], stdin=subprocess.PIPE)
    try:
        stream.main(args.duration, out=mpv.stdin)
    except KeyboardInterrupt:
        pass
    finally:
        mpv.stdin.close(); mpv.wait()

def cmd_control(args):
    from . import control
    control.serve(args.ip, args.port)

def main():
    p = argparse.ArgumentParser(prog="cosmic")
    sub = p.add_subparsers(dest="cmd", required=True)

    o = sub.add_parser("offline", help="write a WAV")
    o.add_argument("--duration", type=int, default=60)
    o.set_defaults(func=cmd_offline)

    t = sub.add_parser("train", help="train the brain from telemetry")
    t.add_argument("--log", default="cosmic_telemetry.jsonl")
    t.add_argument("--out", default="cosmic_brain.npz")
    t.set_defaults(func=cmd_train)

    l = sub.add_parser("live", help="stream in real time to mpv")
    l.add_argument("--duration", type=int, default=0)   # 0 = infinite
    l.set_defaults(func=cmd_live)

    c = sub.add_parser("control", help="run OSC control server")
    c.add_argument("--ip", default="127.0.0.1")
    c.add_argument("--port", type=int, default=9000)
    c.set_defaults(func=cmd_control)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
