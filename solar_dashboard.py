import sys, json, time, numpy as np

# reads Gohm's strategy log and renders live dashboard
def render(strategy_log, telem):
    os.system("clear")
    print("=" * 60)
    print("  ☀️  SOLAR ACOUSTIC SIMULATOR — AIDEN & GOHM DASHBOARD")
    print("=" * 60)

    if telem:
        last = telem[-1]
        print(f"\n  Generation:     {last.get('gen', '?')}")
        print(f"  Spectral entropy: {last.get('entropy', 0):.3f}")
        print(f"  Peak p-mode:    {last.get('peak_hz', 0):.2f} Hz")
        print(f"  Coupling:       {last.get('coupling', 0):.3f}")
        print(f"  Solar cycle:    {last.get('cycle_amp', 0)*100:.0f}%")
        print(f"  Strategies:     {', '.join(last.get('strategies', []))}")

    print(f"\n  Total generations: {len(strategy_log)}")
    print("=" * 60)

if __name__ == "__main__":
    print("Dashboard runs alongside solar_acoustic_sim.py")
    print("Press Ctrl+C to exit")
