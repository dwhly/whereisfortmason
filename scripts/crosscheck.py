#!/usr/bin/env python3
"""Fort Mason address cross-check: what each public data source says for every Fort Mason address.

Sources (all public, no keys):
  - OpenStreetMap (Overpass): addr:housenumber/addr:street on Fort Mason buildings
  - City and County of San Francisco Enterprise Addressing System (EAS), DataSF dataset 3mea-di5p
  - U.S. Census Bureau geocoder (TIGER address ranges), benchmark Public_AR_Current
Writes evidence/crosscheck-<date>.json and prints a table. Re-run any time to see whether a fix has landed.
"""
import json, math, time, urllib.parse, urllib.request, datetime, pathlib

BBOX = (37.8020, -122.4345, 37.8095, -122.4235)  # Upper Fort Mason + Fort Mason Center
UA = {"User-Agent": "fort-mason-addressing/1.0 (community address-accuracy project)"}
OUT = pathlib.Path(__file__).resolve().parent.parent / "evidence"


def fetch(url, data=None, timeout=120):
    err = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=UA), timeout=timeout) as r:
                return r.read().decode()
        except Exception as e:  # transient 504/connection resets are common on Overpass/DataSF
            err = e
            time.sleep(5)
    raise err


def osm():
    s, w, n, e = BBOX
    q = f'[out:json][timeout:90];nwr["addr:housenumber"]["addr:street"="Fort Mason"]({s},{w},{n},{e});out center tags;'
    for ep in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"):
        try:
            j = json.loads(fetch(ep, data=urllib.parse.urlencode({"data": q}).encode()))
            break
        except Exception:
            j = None
    rows = []
    for el in (j or {}).get("elements", []):
        c = el.get("center") or {"lat": el.get("lat"), "lon": el.get("lon")}
        t = el["tags"]
        rows.append({"number": t["addr:housenumber"], "lat": c["lat"], "lon": c["lon"], "name": t.get("name", ""),
                     "building": t.get("building", ""), "osm": f'{el["type"]}/{el["id"]}'})
    return rows


def eas():
    s, w, n, e = BBOX
    where = f"latitude between {s} and {n} and longitude between {w} and {e}"
    j = json.loads(fetch("https://data.sfgov.org/resource/3mea-di5p.json?" + urllib.parse.urlencode(
        {"$where": where, "$limit": 5000,
         "$select": "address,address_number,street_name,street_type,zip_code,latitude,longitude,complete_landmark_name,landmark_aliases,parcel_number,eas_baseid"})))
    return [r for r in j if r.get("zip_code") == "94123" and (
        r.get("street_name") in ("MACARTHUR", "POPE", "FUNSTON")
        or (r.get("street_name") == "FRANKLIN" and float(r.get("address_number") or 0) < 1000))]


def census(address):
    j = json.loads(fetch("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?" + urllib.parse.urlencode(
        {"address": address, "benchmark": "Public_AR_Current", "format": "json"})))
    return [{"matched": m["matchedAddress"], "lat": m["coordinates"]["y"], "lon": m["coordinates"]["x"]}
            for m in j["result"]["addressMatches"]]


def dist_m(a, b):
    return math.hypot((a[0] - b[0]) * 111_000, (a[1] - b[1]) * 88_000)


def main():
    o, c = osm(), eas()
    table = []
    for r in sorted(o, key=lambda r: int("".join(ch for ch in r["number"] if ch.isdigit()) or 0)):
        p = (r["lat"], r["lon"])
        near = min(c, key=lambda x: dist_m(p, (float(x["latitude"]), float(x["longitude"])))) if c else None
        nd = dist_m(p, (float(near["latitude"]), float(near["longitude"]))) if near else None
        fm = census(f'{r["number"]} Fort Mason, San Francisco, CA 94123')
        city = census(f'{near["address"]}, San Francisco, CA') if near and nd is not None and nd < 15 else []
        far = [m for m in city if dist_m(p, (m["lat"], m["lon"])) > 500]
        table.append({"resident_address": f'{r["number"]} Fort Mason', "osm_name": r["name"], "osm": r["osm"],
                      "lat": r["lat"], "lon": r["lon"],
                      "city_eas_address": near["address"] if near and nd < 15 else None,
                      "city_eas_distance_m": round(nd) if nd is not None else None,
                      "census_fort_mason_matches": len(fm),
                      "census_city_address_matches": [m["matched"] for m in city],
                      "city_address_also_exists_elsewhere": [f'{m["matched"]} ({dist_m(p, (m["lat"], m["lon"]))/1000:.1f} km away)' for m in far]})
    OUT.mkdir(exist_ok=True)
    f = OUT / f"crosscheck-{datetime.date.today().isoformat()}.json"
    f.write_text(json.dumps({"generated": datetime.datetime.utcnow().isoformat() + "Z", "rows": table,
                             "eas_points": c, "osm_points": o}, indent=1))
    print(f"{'resident address':<18} {'OSM name':<26} {'city (EAS) address':<22} {'Census: N Fort Mason':<20} same city address elsewhere")
    for t in table:
        print(f"{t['resident_address']:<18} {t['osm_name'][:25]:<26} {str(t['city_eas_address'] or '-'):<22} "
              f"{('no match' if not t['census_fort_mason_matches'] else str(t['census_fort_mason_matches'])+' match'):<20} "
              f"{'; '.join(t['city_address_also_exists_elsewhere']) or '-'}")
    print(f"\nwrote {f}")


if __name__ == "__main__":
    main()
