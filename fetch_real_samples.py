#!/usr/bin/env python3
"""
Download real disaster sounds from Wikimedia Commons + Internet Archive.
"""
import json, subprocess, sys, time
import urllib.parse, urllib.request
from pathlib import Path

SAMPLES_DIR = Path("real_samples")
SAMPLES_DIR.mkdir(exist_ok=True)

# Wikimedia Commons
WIKI_API = "https://commons.wikimedia.org/w/api.php"

# Internet Archive
IA_SEARCH = "https://archive.org/advancedsearch.php"

# Category → search terms
QUERIES = {
    "earthquake": ["earthquake sound", "earthquake"],
    "volcano":    ["volcano eruption", "volcanic"],
    "storm":      ["thunderstorm", "thunder"],
    "wind":       ["wind", "gale"],
    "fire":       ["fireplace", "campfire"],
    "wave":       ["ocean waves", "surf"],
    "tremor":     ["earth tremor", "rumble"],
    "explosion":  ["explosion", "detonation"],
}


def wiki_search(query, limit=5):
    """Search Wikimedia Commons for audio files."""
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{query} filetype:audio",
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
    }
    url = WIKI_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": "cosmic-arabic-noise/1.0 (https://github.com/zeitgeistksa-cyber)",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"   wiki search failed: {e}", file=sys.stderr)
        return []

    results = []
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        info = page.get("imageinfo", [{}])[0]
        mime = info.get("mime", "")
        if not mime.startswith("audio/"):
            continue
        url_ = info.get("url")
        size = info.get("size", 0)
        if not url_ or size > 30_000_000:
            continue
        results.append((page.get("title", "?"), url_, size))
    return results


def ia_search(query, limit=5):
    """Search Internet Archive for audio items."""
    params = {
        "q": f"({query}) AND mediatype:(audio)",
        "fl[]": ["identifier", "title"],
        "rows": str(limit),
        "output": "json",
    }
    url = IA_SEARCH + "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"User-Agent": "cosmic-arabic-noise/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"   IA search failed: {e}", file=sys.stderr)
        return []

    results = []
    for doc in data.get("response", {}).get("docs", []):
        ident = doc.get("identifier")
        title = doc.get("title", ident)
        if ident:
            # Files can be at https://archive.org/download/{ident}/
            results.append((ident, title))
    return results


def ia_files(identifier):
    """Return list of audio file URLs for an IA item."""
    url = f"https://archive.org/metadata/{identifier}"
    req = urllib.request.Request(url, headers={"User-Agent": "cosmic-arabic-noise/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
    except Exception:
        return []

    files = []
    for f in data.get("files", []):
        name = f.get("name", "")
        fmt = f.get("format", "").lower()
        if any(name.lower().endswith(ext) for ext in
               [".mp3", ".ogg", ".wav", ".flac", ".m4a"]):
            size = int(f.get("size", 0))
            if size < 30_000_000:
                files.append(f"https://archive.org/download/{identifier}/{name}")
    return files


def download(url, dest):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "cosmic-arabic-noise/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            dest.write_bytes(r.read())
        return dest.stat().st_size > 1000
    except Exception as e:
        print(f"      download failed: {e}", file=sys.stderr)
        return False


def to_wav_mono(src, dest):
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", str(src),
             "-ac", "1", "-ar", "44100",
             "-acodec", "pcm_s16le",
             str(dest)],
            capture_output=True, timeout=120,
        )
        return r.returncode == 0 and dest.exists()
    except Exception as e:
        print(f"      convert failed: {e}", file=sys.stderr)
        return False


def try_wiki(category, query):
    """Try Wikimedia Commons. Return saved paths."""
    print(f"   [wiki] {query}")
    results = wiki_search(query, limit=5)
    print(f"      {len(results)} results")
    saved = []
    for i, (title, url, size) in enumerate(results[:3]):
        ext = Path(urllib.parse.urlparse(url).path).suffix or ".ogg"
        raw = SAMPLES_DIR / f"{category}_w{i}{ext}"
        wav = SAMPLES_DIR / f"{category}_w{i}.wav"
        if not download(url, raw):
            continue
        if not to_wav_mono(raw, wav):
            raw.unlink(missing_ok=True)
            continue
        raw.unlink(missing_ok=True)
        print(f"      saved {wav.name} ({wav.stat().st_size//1024} KB)")
        saved.append(wav)
    return saved


def try_ia(category, query):
    """Try Internet Archive. Return saved paths."""
    print(f"   [IA] {query}")
    results = ia_search(query, limit=5)
    print(f"      {len(results)} results")
    saved = []
    for ident, title in results[:3]:
        files = ia_files(ident)
        if not files:
            continue
        # take first audio file
        url = files[0]
        ext = Path(urllib.parse.urlparse(url).path).suffix or ".mp3"
        raw = SAMPLES_DIR / f"{category}_ia{len(saved)}{ext}"
        wav = SAMPLES_DIR / f"{category}_ia{len(saved)}.wav"
        if not download(url, raw):
            continue
        if not to_wav_mono(raw, wav):
            raw.unlink(missing_ok=True)
            continue
        raw.unlink(missing_ok=True)
        print(f"      saved {wav.name} ({wav.stat().st_size//1024} KB)")
        saved.append(wav)
        if len(saved) >= 2:
            break
    return saved


def main():
    print("=" * 60)
    print("FETCHING REAL DISASTER SAMPLES (multi-source)")
    print("=" * 60)

    manifest = {}
    for category, queries in QUERIES.items():
        print(f"\n>> {category.upper()}")
        saved = []
        # Try Wikimedia, then Internet Archive
        for q in queries:
            saved = try_wiki(category, q)
            if saved:
                break
        if not saved:
            for q in queries:
                saved = try_ia(category, q)
                if saved:
                    break
        if saved:
            manifest[category] = [str(p) for p in saved]
        time.sleep(2)  # be polite

    Path("real_samples/manifest.json").write_text(json.dumps(manifest, indent=2))
    total = sum(len(v) for v in manifest.values())
    print(f"\n>> Downloaded {total} samples across {len(manifest)} categories")
    print(f">> Manifest: real_samples/manifest.json")

    if total == 0:
        print("\n!! Nothing downloaded. Possible causes:")
        print("   - No internet")
        print("   - Both archives rate-limiting")
        print("   - ffmpeg missing (check: which ffmpeg)")


if __name__ == "__main__":
    main()
