import json, time
from collections import Counter
from pathlib import Path

while True:
    if not Path("channel_log.jsonl").exists():
        time.sleep(30); continue
    books = Counter(); roots = Counter()
    total = 0
    for line in open("channel_log.jsonl", encoding="utf-8"):
        try: r = json.loads(line)
        except: continue
        books[r["book"]] += 1
        roots[r["root"]] += 1
        total += 1
    print(f"\n=== Total roots played: {total} ===")
    print("Top books:")
    for b, n in books.most_common(5):
        print(f"  {b[:40]:40s}  {n}")
    print("Top roots:")
    for r, n in roots.most_common(10):
        print(f"  {r}  x{n}")
    time.sleep(60)
