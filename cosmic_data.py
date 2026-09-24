#!/usr/bin/env python3
"""
Cosmic Data Fetcher
===================
Pulls live data from:
  - SunGeo.net: Schumann resonance, Kp index, solar wind
  - NOAA SWPC: real-time solar wind, Kp, X-ray flux
  - NASA DONKI: solar flares, CMEs, geomagnetic storms

All sources are free, no API keys. Results cached for 60s.
"""
import json, time, urllib.request, urllib.error
from pathlib import Path

CACHE_DIR = Path("cosmic_cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL = 60  # seconds

def _fetch(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "cosmic-noise/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        return None

def _cached(name, url):
    path = CACHE_DIR / f"{name}.json"
    if path.exists() and (time.time() - path.stat().st_mtime) < CACHE_TTL:
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    raw = _fetch(url)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        path.write_text(json.dumps(data))
        return data
    except json.JSONDecodeError:
        return None

def get_schumann():
    """Live Schumann resonance + Kp index from SunGeo.net."""
    return _cached("sungeo_current", "https://sungeo.net/api/current")

def get_schumann_history(days=7):
    """Daily Schumann score averages."""
    return _cached(f"sungeo_history_{days}",
                   f"https://sungeo.net/api/history?days={days}")

def get_solar_wind():
    """Real-time solar wind plasma from NOAA SWPC."""
    return _cached("noaa_solar_wind_plasma",
                   "https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json")

def get_solar_wind_mag():
    """Real-time solar wind magnetic field from NOAA SWPC."""
    return _cached("noaa_solar_wind_mag",
                   "https://services.swpc.noaa.gov/products/solar-wind/mag-7-day.json")

def get_kp_index():
    """Real-time planetary K-index from NOAA SWPC."""
    return _cached("noaa_kp",
                   "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json")

def get_goes_xray():
    """GOES X-ray flux (solar flare activity) from NOAA SWPC."""
    return _cached("noaa_goes_xray",
                   "https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json")

def get_donki_flares(days=7):
    """NASA DONKI solar flares from the last N days."""
    end = time.strftime("%Y-%m-%d")
    start = time.strftime("%Y-%m-%d", time.localtime(time.time() - days*86400))
    url = (f"https://api.nasa.gov/DONKI/FLR?startDate={start}&endDate={end}"
           f"&api_key=DEMO_KEY")
    return _cached(f"donki_flares_{days}", url)

def get_donki_cme(days=7):
    """NASA DONKI coronal mass ejections from the last N days."""
    end = time.strftime("%Y-%m-%d")
    start = time.strftime("%Y-%m-%d", time.localtime(time.time() - days*86400))
    url = (f"https://api.nasa.gov/DONKI/CME?startDate={start}&endDate={end}"
           f"&api_key=DEMO_KEY")
    return _cached(f"donki_cme_{days}", url)

def snapshot():
    """Return a compact dict of current cosmic state."""
    out = {"ts": time.time()}

    # Schumann / SunGeo composite
    sch = get_schumann()
    if sch:
        out["schumann_status"] = sch.get("status")
        out["schumann_score"] = sch.get("score")
        out["kp_value"] = sch.get("kp_value")
        out["kp_text"] = sch.get("kp_text")
        solar = sch.get("solar", {}) or {}
        out["wind_speed"] = solar.get("wind_speed")
        if "bz" in solar:
            out["bz"] = solar.get("bz")

    # NOAA Kp latest
    kp = get_kp_index()
    if kp and isinstance(kp, list) and len(kp) > 1:
        out["kp_latest"] = kp[-1]

    # NOAA solar wind plasma (density, speed)
    plasma = get_solar_wind()
    if plasma and isinstance(plasma, list) and len(plasma) > 1:
        try:
            latest_p = plasma[-1]
            if len(latest_p) >= 3:
                if out.get("wind_speed") is None:
                    out["wind_speed"] = float(latest_p[2])
                out["density"] = float(latest_p[1])
        except (ValueError, IndexError, TypeError):
            pass

    # NOAA magnetometer — Bz extraction
    mag = get_solar_wind_mag()
    if mag and isinstance(mag, list) and len(mag) > 1:
        try:
            latest_m = mag[-1]
            # NOAA format: [time, bx, by, bz, lon, lat, bt]
            if len(latest_m) >= 4:
                bz_val = latest_m[3]
                if bz_val not in (None, "", "null"):
                    out["bz"] = float(bz_val)
        except (ValueError, IndexError, TypeError):
            pass

    # Fallback: try the SunGeo solar.bz field
    if out.get("bz") is None and sch:
        solar2 = sch.get("solar", {}) or {}
        if solar2.get("bz") is not None:
            try:
                out["bz"] = float(solar2["bz"])
            except (ValueError, TypeError):
                pass

    # X-ray latest
    xray = get_goes_xray()
    if xray and isinstance(xray, list) and len(xray) > 0:
        out["xray_latest"] = xray[-1]

    return out

if __name__ == "__main__":
    s = snapshot()
    print(json.dumps(s, indent=2))
