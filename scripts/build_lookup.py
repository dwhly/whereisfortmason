#!/usr/bin/env python3
"""Build data/lookup/fort-mason.json for the site's "Where does it send you?" tool.

For each Fort Mason address (data/truth/fort-mason.csv):
  - where each OPEN system puts it (US Census geocoder, OSM Nominatim, Photon) with coordinates, distance, and what is
    actually at the wrong spot (Nominatim reverse lookup)
  - the City's official address at that spot (EAS, from evidence/crosscheck-*.json) and its twin elsewhere in SF
Commercial systems (Apple, Google, ...) are not stored here; their terms restrict storing results.
Data: US Census (public domain); OpenStreetMap contributors (ODbL); DataSF EAS (PDDL).
"""
import csv, glob, json, math, pathlib, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "fort-mason-address-challenge/0.1 (github.com/dwhly/whereisfortmason)"}
CITY = "San Francisco, CA 94123"


def get(url):
    err = None
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            err = e
            time.sleep(3 * (i + 1))
    raise err


def dist_m(a, b):
    return math.hypot((a[0] - b[0]) * 111_000, (a[1] - b[1]) * 88_000)


def census(q):
    j = get("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?" + urllib.parse.urlencode(
        {"address": q, "benchmark": "Public_AR_Current", "format": "json"}))
    return [(m["coordinates"]["y"], m["coordinates"]["x"], m["matchedAddress"]) for m in j["result"]["addressMatches"]]


def nominatim(q):
    time.sleep(1.1)
    j = get("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": q, "format": "jsonv2", "limit": 1, "countrycodes": "us"}))
    return (float(j[0]["lat"]), float(j[0]["lon"]), j[0].get("display_name", "")) if j else None


def photon(q):
    j = get("https://photon.komoot.io/api/?" + urllib.parse.urlencode({"q": q, "limit": 1, "lat": 37.806, "lon": -122.427}))
    f = j.get("features") or []
    if not f:
        return None
    p = f[0]["properties"]
    label = " ".join(str(x) for x in (p.get("name"), p.get("housenumber"), p.get("street")) if x)
    return (f[0]["geometry"]["coordinates"][1], f[0]["geometry"]["coordinates"][0], label)


def whats_here(lat, lon):
    time.sleep(1.1)
    j = get("https://nominatim.openstreetmap.org/reverse?" + urllib.parse.urlencode({"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 18}))
    a = j.get("address", {})
    name = j.get("name") or ""
    num = a.get("house_number", "")
    road = a.get("road") or a.get("pedestrian") or a.get("footway") or ""
    place = name or " ".join(x for x in (num, road) if x) or (j.get("display_name", "").split(",")[0])
    near = a.get("neighbourhood") or a.get("suburb") or ""
    return f"{place}" + (f" ({near})" if near and near not in place else "")


def main():
    truth = list(csv.DictReader(open(ROOT / "data" / "truth" / "fort-mason.csv")))
    cross = json.load(open(sorted(glob.glob(str(ROOT / "evidence" / "crosscheck-*.json")))[-1]))
    city = {r["resident_address"]: r for r in cross["rows"]}
    out = []
    for t in truth:
        a = t["address"]
        door = (float(t["lat"]), float(t["lon"]))
        q = f"{a}, {CITY}"
        rec = {"address": a, "building": t["building"], "door": door, "systems": {}}
        for name, fn in (("US Census", lambda q: (census(q) or [None])[0]), ("OSM Nominatim", nominatim), ("Photon (OSM)", photon)):
            try:
                r = fn(q)
            except Exception as e:
                rec["systems"][name] = {"status": "error"}
                continue
            if not r:
                rec["systems"][name] = {"status": "not_found"}
                continue
            d = dist_m(door, r[:2])
            s = {"status": "pass" if d <= 60 else "wrong", "at": [round(r[0], 6), round(r[1], 6)], "m": round(d), "label": r[2]}
            if d > 60:
                s["whats_there"] = whats_here(*r[:2])
            rec["systems"][name] = s
        c = city.get(a)
        if c and c.get("city_eas_address"):
            rec["city_name"] = c["city_eas_address"].title().replace(" St", " St").replace(" Ave", " Ave")
            try:
                twins = [m for m in census(f'{c["city_eas_address"]}, San Francisco, CA') if dist_m(door, m[:2]) > 500]
            except Exception:
                twins = []
            if twins:
                m = twins[0]
                rec["city_twin"] = {"at": [round(m[0], 6), round(m[1], 6)], "km": round(dist_m(door, m[:2]) / 1000, 1),
                                    "label": m[2].title(), "whats_there": whats_here(m[0], m[1])}
        out.append(rec)
        print(a, {k: v.get("status") for k, v in rec["systems"].items()}, rec.get("city_name"), "twin" if rec.get("city_twin") else "", flush=True)
    d = ROOT / "data" / "lookup"
    d.mkdir(parents=True, exist_ok=True)
    (d / "fort-mason.json").write_text(json.dumps({"generated": time.strftime("%Y-%m-%d"), "addresses": out}, indent=1))
    print("wrote", d / "fort-mason.json")


if __name__ == "__main__":
    main()
