#!/usr/bin/env python3
"""
Arabic Text-to-Sound Channel
Reads books from ./books, extracts roots from each line,
synthesizes them as continuous audio. Loops forever.
"""
import sys, time, json, random, glob, re
from pathlib import Path
import numpy as np
from phoneme_table import PHONEMES, root_to_log_triad
from phoneme_grammar import VOICED, EMPHATIC, MANNER
from extract_roots import triliteral_skeleton

SR = 44100
CHUNK = 2048
ROOT_DUR = 0.9          # seconds per root — fast chant pace
GAP_DUR = 0.10
BOOKS_DIR = Path("books")
STATE_FILE = Path("channel_state.json")
LOG_FILE = Path("channel_log.jsonl")

# ---------- Audio synthesis (same as poem engine) ----------
def char(c):
    if c not in PHONEMES: return 0.0, 0.0
    voice = 1.0 if c in VOICED else 0.0
    emph = 1.0 if c in EMPHATIC else 0.0
    manner = MANNER.get(c, 0.5)
    return (voice * (1.0 - manner) * 0.5 + emph * 0.3, manner * 0.4)

def synth_root(root, sr=SR, dur=ROOT_DUR):
    if len(root) != 3 or root_to_log_triad(root) is None:
        return None
    f1, f2, f3 = root_to_log_triad(root)
    letters = list(root)
    n = int(sr * dur)
    t = np.arange(n) / sr
    pos = np.linspace(0, 1, n)

    def env(s, e):
        c = 0.5 * (s + e); h = 0.5 * (e - s) + 1e-9
        return np.maximum(0.0, 1.0 - np.abs(pos - c) / h)

    e1, e2, e3 = env(0, .42), env(.29, .71), env(.58, 1)
    triad = (e1*np.sin(2*np.pi*f1*t) + e2*np.sin(2*np.pi*f2*t)
             + e3*np.sin(2*np.pi*f3*t))
    s0, h0 = char(letters[0]); s1, h1 = char(letters[1]); s2, h2 = char(letters[2])
    sub = (s0*e1 + s1*e2 + s2*e3) * np.sin(2*np.pi*35*t)
    hiss = (h0*e1 + h1*e2 + h2*e3) * np.random.randn(n)
    mixed = triad*0.62 + sub*0.18 + hiss*0.12
    sat = np.tanh(np.sin(mixed*2.2) * 2.8)
    fade_n = int(sr * 0.03)
    if fade_n > 0:
        fade = np.linspace(0, 1, fade_n)
        sat[:fade_n] *= fade
        sat[-fade_n:] *= fade[::-1]
    peak = np.max(np.abs(sat)) + 1e-9
    return (sat / peak * 0.95).astype(np.float32)

# ---------- Book iteration ----------
def find_books():
    """Return list of text files in books/ recursively."""
    exts = ("*.txt", "*.mARkdown", "*.md")
    files = []
    for ext in exts:
        files.extend(glob.glob(str(BOOKS_DIR / "**" / ext), recursive=True))
    return sorted(files)

def iter_lines(book_path):
    """Yield non-empty lines from a book file."""
    try:
        with open(book_path, encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                line = line.strip()
                # Skip metadata lines, page numbers, headers
                if len(line) < 3: continue
                if line.startswith("#"): continue
                if line.startswith("###"): continue
                if re.match(r"^\d+$", line): continue
                yield line
    except Exception as e:
        print(f"!! failed reading {book_path}: {e}", file=sys.stderr)

# ---------- State management ----------
def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {"book_idx": 0, "line_idx": 0, "session_start": time.time()}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def log_entry(entry):
    with open(LOG_FILE, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")

# ---------- Main loop ----------
def main():
    books = find_books()
    if not books:
        print("!! no books found in ./books — see instructions")
        sys.exit(1)
    print(f">> {len(books)} books found", file=sys.stderr)

    state = load_state()
    book_idx = state["book_idx"] % len(books)
    line_idx = state["line_idx"]

    roots_since_restart = 0
    while True:
        book_path = books[book_idx]
        book_name = Path(book_path).stem
        print(f"\n>> Book {book_idx+1}/{len(books)}: {book_name} (line {line_idx})",
              file=sys.stderr)

        any_line = False
        for line in iter_lines(book_path):
            any_line = True
            if line_idx > 0:
                line_idx -= 1
                continue

            # Extract all roots from this line
            words = line.split()
            line_roots = []
            for w in words[:8]:   # cap per line to keep pace
                r = triliteral_skeleton(w)
                if r and len(r) == 3 and all(c in PHONEMES for c in r):
                    line_roots.append(r)

            if not line_roots:
                continue

            # Emit each root as audio
            for root in line_roots:
                samples = synth_root(root)
                if samples is None:
                    continue
                # stereo
                delay = int(SR * 0.004)
                left = samples
                right = np.concatenate([np.zeros(delay, dtype=np.float32),
                                        samples[:-delay]])
                stereo = np.stack([left, right], axis=1)
                int16 = (np.clip(stereo, -1.0, 1.0) * 32767).astype(np.int16)
                sys.stdout.buffer.write(int16.tobytes())
                sys.stdout.buffer.flush()

                # Silence gap
                gap_n = int(SR * GAP_DUR)
                gap = np.zeros((gap_n, 2), dtype=np.int16)
                sys.stdout.buffer.write(gap.tobytes())
                sys.stdout.buffer.flush()

                roots_since_restart += 1

                log_entry({
                    "ts": time.time(),
                    "book": book_name,
                    "book_idx": book_idx,
                    "line": line[:80],
                    "root": root,
                    "roots_total": roots_since_restart,
                })

        # Book finished — move to next
        if not any_line:
            print(f"!! empty book {book_name}", file=sys.stderr)

        book_idx = (book_idx + 1) % len(books)
        line_idx = 0
        state["book_idx"] = book_idx
        state["line_idx"] = 0
        save_state(state)
        print(f">> finished book, moving to book {book_idx+1}", file=sys.stderr)

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        print("\n>> channel stopped", file=sys.stderr)
