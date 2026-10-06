#!/usr/bin/env python3
"""Fort Mason Address Challenge scoreboard.

For every Fort Mason address in data/truth/fort-mason.csv, ask each map system where it is, and score PASS if the
answer lands within PASS_M metres of the true building. One cell per (address, system). The challenge is won system by
system, as each column turns green.

Systems tested without keys: US Census geocoder, OpenStreetMap Nominatim, Photon (Komoot; OSM-based).
Systems that need a key (env var), skipped if unset:
  APPLE_MAPS_TOKEN  Apple Maps Server API /v1/geocode   (Apple Developer account)
  GOOGLE_MAPS_KEY   Google Geocoding API
  HERE_API_KEY, TOMTOM_API_KEY, MAPBOX_TOKEN, ESRI_API_KEY
Only PASS/FAIL and distance are written to the repo; raw results from commercial services are not stored (their
terms restrict caching and redistribution).
"""
import csv, json, math, os, pathlib, time, urllib.parse, urllib.request, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "fort-mason-address-challenge/0.1 (github.com/dwhly/whereisfortmason)"}
PASS_M = 60
CITY = "San Francisco, CA 94123"


def get(url, headers=None, timeout=60):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={**UA, **(headers or {})}), timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            err = e
            time.sleep(3 * (i + 1))
    raise err


def dist_m(a, b):
    return math.hypot((a[0] - b[0]) * 111_000, (a[1] - b[1]) * 88_000)


def census(addr):
    j = get("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?" + urllib.parse.urlencode(
        {"address": f"{addr}, {CITY}", "benchmark": "Public_AR_Current", "format": "json"}))
    m = j["result"]["addressMatches"]
    return (m[0]["coordinates"]["y"], m[0]["coordinates"]["x"]) if m else None


def nominatim(addr):
    time.sleep(1.1)  # usage policy: max 1 request/second
    j = get("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": f"{addr}, {CITY}", "format": "jsonv2", "limit": 1, "countrycodes": "us"}))
    return (float(j[0]["lat"]), float(j[0]["lon"])) if j else None


def photon(addr):
    j = get("https://photon.komoot.io/api/?" + urllib.parse.urlencode(
        {"q": f"{addr}, {CITY}", "limit": 1, "lat": 37.806, "lon": -122.427}))
    f = j.get("features") or []
    return (f[0]["geometry"]["coordinates"][1], f[0]["geometry"]["coordinates"][0]) if f else None


def apple(addr):
    tok = os.environ.get("APPLE_MAPS_TOKEN")
    if not tok:
        return "NO_KEY"
    auth = get("https://maps-api.apple.com/v1/token", headers={"Authorization": f"Bearer {tok}"})
    j = get("https://maps-api.apple.com/v1/geocode?" + urllib.parse.urlencode({"q": f"{addr}, {CITY}", "limitToCountries": "US"}),
            headers={"Authorization": f'Bearer {auth["accessToken"]}'})
    r = j.get("results") or []
    return (r[0]["coordinate"]["latitude"], r[0]["coordinate"]["longitude"]) if r else None


def google(addr):
    key = os.environ.get("GOOGLE_MAPS_KEY")
    if not key:
        return "NO_KEY"
    j = get("https://maps.googleapis.com/maps/api/geocode/json?" + urllib.parse.urlencode({"address": f"{addr}, {CITY}", "key": key}))
    r = j.get("results") or []
    return (r[0]["geometry"]["location"]["lat"], r[0]["geometry"]["location"]["lng"]) if r else None


SYSTEMS = [("Apple Maps", apple), ("Google", google), ("US Census", census), ("OSM Nominatim", nominatim), ("Photon (OSM)", photon)]


def main():
    truth = list(csv.DictReader(open(ROOT / "data" / "truth" / "fort-mason.csv")))
    rows, score = [], {s: [0, 0] for s, _ in SYSTEMS}
    for t in truth:
        p = (float(t["lat"]), float(t["lon"]))
        row = {"address": t["address"], "building": t["building"]}
        for name, fn in SYSTEMS:
            try:
                r = fn(t["address"])
            except Exception as e:
                r = f"ERROR {type(e).__name__}"
            if r == "NO_KEY" or (isinstance(r, str) and r.startswith("ERROR")):
                row[name] = r if r == "NO_KEY" else "ERROR"
                continue
            if r is None:
                row[name] = "FAIL (not found)"
            else:
                d = dist_m(p, r)
                row[name] = f"PASS ({d:.0f} m)" if d <= PASS_M else f"FAIL ({d:.0f} m off)"
            score[name][1] += 1
            score[name][0] += row[name].startswith("PASS")
        rows.append(row)
        print(row, flush=True)
    out = ROOT / "data" / "scoreboard"
    out.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    (out / f"{today}.json").write_text(json.dumps({"date": today, "pass_m": PASS_M, "rows": rows, "score": score}, indent=1))
    md = [f"# Fort Mason Address Challenge: scoreboard ({today})", "",
          f"PASS = the address people use lands within {PASS_M} m of the right building.", "",
          "| System | Score |", "|---|---|"]
    for name, _ in SYSTEMS:
        ok, n = score[name]
        md.append(f"| {name} | {'not yet tested (needs key)' if n == 0 else f'**{ok} / {n}**'} |")
    md += ["", "| Address | Building | " + " | ".join(n for n, _ in SYSTEMS) + " |", "|---|---|" + "---|" * len(SYSTEMS)]
    for r in rows:
        md.append(f'| {r["address"]} | {r["building"]} | ' + " | ".join(r.get(n, "") for n, _ in SYSTEMS) + " |")
    (ROOT / "SCOREBOARD.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:12]))


if __name__ == "__main__":
    main()
