from pathlib import Path
p = Path("dialogue_engine.py")
s = p.read_text()

before = s
s = s.replace("ar * 0.25", "ar * 0.10")
s = s.replace("triad_direct[:, None] * 0.60",
              "triad_direct[:, None] * 0.85")

if s != before:
    p.write_text(s)
    print(">> PATCH APPLIED")
else:
    print(">> NO CHANGE — patterns not found")
