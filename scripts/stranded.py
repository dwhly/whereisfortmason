#!/usr/bin/env python3
"""Stranded-address detector for San Francisco areas.

For every address people actually use in an area (OpenStreetMap addr:* tags), compare against the City and County of
San Francisco's official address points (Enterprise Addressing System, DataSF 3mea-di5p) and classify:

  MATCH          the City has the same number + street at that spot (within MATCH_M metres)
  TWO_SYSTEMS    the City has that spot under a DIFFERENT address (e.g. "3 Fort Mason" vs "3 Franklin St")
  NO_OFFICIAL    the City has no address point at that spot at all (nearest is farther than NEAR_M)

and, for every official address in the area:

  TWIN_ELSEWHERE the same number + street also exists elsewhere in San Francisco, more than TWIN_KM away
                 (a geocoder that ignores ZIP/unit context can send a driver there)

Usage: python3 scripts/stranded.py [area ...]     (default: all areas in data/areas.json)
Outputs: data/stranded/<area>.csv and data/stranded/summary.md
Data: OpenStreetMap (c) OpenStreetMap contributors, ODbL. DataSF EAS: ODC PDDL. All public, no API keys.
"""
import csv, json, math, pathlib, sys, time, urllib.parse, urllib.request, datetime, re
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "stranded-addresses/0.1 (open community project; github.com/dwhly/whereisfortmason)"}
MATCH_M, NEAR_M, TWIN_KM = 40, 20, 1.0
SUFFIX = {"STREET": "ST", "AVENUE": "AVE", "ROAD": "RD", "DRIVE": "DR", "BOULEVARD": "BLVD", "COURT": "CT", "LANE": "LN",
          "PLACE": "PL", "TERRACE": "TER", "WAY": "WAY", "CIRCLE": "CIR", "PLAZA": "PLZ", "HIGHWAY": "HWY", "ALLEY": "ALY",
          "PARKWAY": "PKWY", "SQUARE": "SQ", "LOOP": "LOOP", "ROW": "ROW", "WALK": "WALK"}


def fetch(url, data=None, timeout=150):
    err = None
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=UA), timeout=timeout) as r:
                return r.read().decode()
        except Exception as e:
            err = e
            time.sleep(4 * (i + 1))
    raise err


def dist_m(a, b):
    return math.hypot((a[0] - b[0]) * 111_000, (a[1] - b[1]) * 88_000)


def norm_street(s):
    w = re.sub(r"[^A-Z0-9 ]", "", (s or "").upper()).split()
    if w and w[-1] in SUFFIX:
        w[-1] = SUFFIX[w[-1]]
    return " ".join(w)


def first_number(s):
    m = re.match(r"\s*(\d+)", s or "")
    return int(m.group(1)) if m else None


def osm_addresses(bbox):
    s, w, n, e = bbox
    q = f'[out:json][timeout:120];nwr["addr:housenumber"]({s},{w},{n},{e});out center tags;'
    for ep in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
               "https://maps.mail.ru/osm/tools/overpass/api/interpreter"):
        try:
            j = json.loads(fetch(ep, data=urllib.parse.urlencode({"data": q}).encode()))
            break
        except Exception:
            j = None
    if j is None:
        raise RuntimeError("all Overpass endpoints failed")
    out = []
    for el in j["elements"]:
        t = el["tags"]
        c = el.get("center") or {"lat": el.get("lat"), "lon": el.get("lon")}
        street = t.get("addr:street") or t.get("addr:place") or ""
        for hn in re.split(r"[;,]", t["addr:housenumber"]):
            num = first_number(hn)
            if num is None or not street:
                continue
            out.append({"num": num, "street": street, "nstreet": norm_street(street), "lat": c["lat"], "lon": c["lon"],
                        "name": t.get("name", ""), "building": t.get("building", ""), "osm": f'{el["type"]}/{el["id"]}'})
    return out


EAS_URL = "https://data.sfgov.org/api/views/3mea-di5p/rows.csv?accessType=DOWNLOAD"
EAS_CACHE = ROOT / "cache" / "eas.csv"
_EAS = None


def eas_all():
    """All official SF address points, from a local cache of the DataSF bulk export (one download, ~70 MB).
    Per-query API calls get rate-limited (connection resets), so everything is computed offline."""
    global _EAS
    if _EAS is None:
        if not EAS_CACHE.exists() or time.time() - EAS_CACHE.stat().st_mtime > 7 * 86400:
            EAS_CACHE.parent.mkdir(exist_ok=True)
            EAS_CACHE.write_text(fetch(EAS_URL, timeout=600))
        _EAS = []
        with open(EAS_CACHE, newline="") as f:
            for r in csv.DictReader(f):
                try:
                    lat, lon = float(r["Latitude"]), float(r["Longitude"])
                except (TypeError, ValueError):
                    continue
                _EAS.append({"address": r["Address"], "address_number": r["Address Number"], "street_name": r["Street Name"],
                             "street_type": r["Street Type"] or None, "zip_code": r["ZIP Code"], "latitude": lat,
                             "longitude": lon, "nhood": r["nhood"], "eas_baseid": r["EAS BaseID"]})
    return _EAS


def eas_in_bbox(s, w, n, e):
    return [dict(r) for r in eas_all() if s <= r["latitude"] <= n and w <= r["longitude"] <= e]


def run(area):
    s, w, n, e = area["bbox"]
    osm = [o for o in osm_addresses(area["bbox"]) if not area.get("osm_street_exclude") or o["nstreet"] not in area["osm_street_exclude"]]
    pad = 0.003  # ~300 m: match against ALL official points near the area, not just the area's own
    eas_near = eas_in_bbox(s - pad, w - pad, n + pad, e + pad)
    for r in eas_near:
        r["p"] = (float(r["latitude"]), float(r["longitude"]))
        r["nstreet"] = norm_street(f'{r.get("street_name", "")} {r.get("street_type", "")}')
        r["num"] = int(float(r["address_number"])) if r.get("address_number") else None
    eas = [r for r in eas_near if s <= r["p"][0] <= n and w <= r["p"][1] <= e
           and (not area.get("eas_nhood") or r.get("nhood") in area["eas_nhood"])]
    # restrict OSM to the area's own official footprint (closer to an in-area official point than to any other)
    if area.get("eas_nhood") and eas:
        others = [r for r in eas_near if r not in eas]
        def in_area(o):
            p = (o["lat"], o["lon"])
            din = min(dist_m(p, r["p"]) for r in eas)
            dout = min((dist_m(p, r["p"]) for r in others), default=1e9)
            return din < 150 and din <= dout
        osm = [o for o in osm if in_area(o)]

    # twins: same number + street elsewhere in SF
    streets = sorted({(r.get("street_name"), r.get("street_type")) for r in eas if r.get("street_name")})
    citywide = defaultdict(list)
    wanted = set(streets)
    for r in eas_all():
        if (r["street_name"], r["street_type"]) in wanted and r.get("address_number"):
            citywide[(int(float(r["address_number"])), r["street_name"], r["street_type"])].append((r["latitude"], r["longitude"], r.get("zip_code")))
    rows = []
    for o in osm:
        p = (o["lat"], o["lon"])
        same = [r for r in eas_near if r["num"] == o["num"] and r["nstreet"] == o["nstreet"] and dist_m(p, r["p"]) <= MATCH_M]
        near = min(eas_near, key=lambda r: dist_m(p, r["p"])) if eas_near else None
        nd = dist_m(p, near["p"]) if near else 1e9
        if same:
            cls, official = "MATCH", same[0]["address"]
        elif nd <= NEAR_M:
            cls, official = "TWO_SYSTEMS", near["address"]
        else:
            cls, official = "NO_OFFICIAL", ""
        ref = same[0] if same else (near if nd <= NEAR_M else None)
        twins = []
        if ref:
            for (lat, lon, z) in citywide.get((ref["num"], ref.get("street_name"), ref.get("street_type")), []):
                dkm = dist_m(ref["p"], (lat, lon)) / 1000
                if dkm > TWIN_KM:
                    twins.append(f"{z} ({dkm:.1f} km away)")
        rows.append({"area": area["id"], "address_people_use": f'{o["num"]} {o["street"]}', "osm_name": o["name"],
                     "lat": round(o["lat"], 6), "lon": round(o["lon"], 6), "class": cls, "official_address_here": official,
                     "nearest_official_m": round(nd) if near else "", "official_twin_elsewhere": "; ".join(sorted(set(twins))),
                     "osm": o["osm"]})
    # official addresses in the area that have a twin elsewhere (whether or not OSM has them)
    twin_official = []
    for r in eas:
        far = [(lat, lon, z) for (lat, lon, z) in citywide.get((r["num"], r.get("street_name"), r.get("street_type")), [])
               if dist_m(r["p"], (lat, lon)) / 1000 > TWIN_KM]
        if far:
            twin_official.append(f'{r["address"]} {r.get("zip_code", "")} -> also {far[0][2]} {dist_m(r["p"], far[0][:2])/1000:.1f} km away')
    return rows, eas, sorted(set(twin_official))


def main():
    areas = json.loads((ROOT / "data" / "areas.json").read_text())
    want = set(sys.argv[1:])
    outdir = ROOT / "data" / "stranded"
    outdir.mkdir(parents=True, exist_ok=True)
    lines = [f"# Stranded-address summary ({datetime.date.today().isoformat()})", "",
             "| Area | Addresses people use (OSM) | MATCH | TWO_SYSTEMS | NO_OFFICIAL | Official addresses | Official address has a twin elsewhere in SF |",
             "|---|---|---|---|---|---|---|"]
    detail = []
    for a in areas:
        if want and a["id"] not in want:
            continue
        rows, eas, twins = run(a)
        with open(outdir / f'{a["id"]}.csv', "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["area"])
            wr.writeheader()
            wr.writerows(rows)
        c = Counter(r["class"] for r in rows)
        lines.append(f'| {a["name"]} | {len(rows)} | {c["MATCH"]} | {c["TWO_SYSTEMS"]} | {c["NO_OFFICIAL"]} | {len(eas)} | {len(twins)} |')
        ex = [r for r in rows if r["class"] != "MATCH"][:8]
        detail += [f'\n## {a["name"]}', ""] + [f'- `{r["address_people_use"]}` ({r["osm_name"] or "-"}): **{r["class"]}**'
                   + (f' (City says `{r["official_address_here"]}`)' if r["official_address_here"] else "")
                   + (f'; City address also exists {r["official_twin_elsewhere"]}' if r["official_twin_elsewhere"] else "") for r in ex]
        if twins:
            detail += ["", "Official addresses here with a twin elsewhere in SF (first 8):"] + [f"- {t}" for t in twins[:8]]
        print(lines[-1], flush=True)
    (outdir / "summary.md").write_text("\n".join(lines + detail) + "\n")
    print(f"\nwrote {outdir}/summary.md")


if __name__ == "__main__":
    main()
