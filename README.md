# Fort Mason addressing project

**Goal:** a Fort Mason resident's address, such as "3 Fort Mason, San Francisco, CA 94123", lands on the right building
in Apple Maps, iPhone "My Location" and the delivery and rideshare apps, as it already does in Google Maps.
**Organised by:** Fort Mason residents. **Started:** 2026-10-05. **Site:** [WhereIsFortMason.com](https://whereisfortmason.com) · **Challenge:** [CHALLENGE.md](CHALLENGE.md)

## 1. What we found on day one (verifiable; re-run `scripts/crosscheck.py`)

Fort Mason has **two address systems for the same buildings**, and most of the data industry only knows one of them:

| Building | What residents, USPS, Zillow and OpenStreetMap use | What the **City's official address database** (EAS) uses |
|---|---|---|
| Haskell House | **3 Fort Mason** | **3 Franklin St** (94123), at the same point to within 1 m |
| Quarters 2 | 2 Fort Mason | 2 Franklin St |
| Quarters 4N/4S | 4 Fort Mason | 4 Franklin St |
| Building 9 | 9 Fort Mason | 9 MacArthur Ave |
| Residences 36, 38, 39 | 36, 38, 39 Fort Mason | 36, 38, 39 MacArthur Ave |

Plus a second gap: **41, 42, 43, 44, 46, 47, 48 and 49 Fort Mason have no City address point at all** within 15 m.
At least some are homes (for example a listing for "48 Fort Mason #11"); for those, the City database has nothing to
return.

Why that breaks things:

1. **"3 Fort Mason" isn't a street anywhere in the government data.** The U.S. Census geocoder, whose TIGER address
   ranges underlie much of the industry and are credited by Apple, returns **no match** for any "N Fort Mason" address.
   A geocoder with no match falls back to a guess: the Fort Mason place pin, another "3" in the complex, or the ZIP code
   centroid.
2. **The City's name collides with the real Franklin Street.** "3 Franklin St, San Francisco" is also an address at
   **Market Street** (ZIP 94102), 3.7 km south. The Census geocoder returns *both* (94102 and 94123) for **2, 3 and
   4 Franklin St**, and for 7. Any system that drops or down-weights the ZIP sends the driver to Market Street. The
   MacArthur Ave addresses have no such twin.
3. **Reverse geocoding ("My Location") returns the City's name.** Standing at Haskell House, the authoritative answer
   is "3 Franklin St". That looks like a different address, and a delivery app that receives it may route to Market St.
4. **Google works** because it builds its own address layer and has learned the "N Fort Mason" names from people and
   businesses.

Apple's own credits page (`gspe21-ssl.ls.apple.com/html/attribution.html`, rev. 09/22/2026) lists **OpenStreetMap,
CoreLogic property-parcel data for the USA, the U.S. Census Bureau, USGS and Esri U.S. Federal datasets**. Those are the
candidate upstream sources for Apple's US addresses. Delivery apps mostly sit on Google Maps Platform, HERE, TomTom,
Mapbox or Esri geocoders, plus USPS-based address validation.

**Hypothesis to prove:** the root cause is the missing "N Fort Mason" form in the **government address chain** (City EAS
→ County assessor parcels → Census TIGER / National Address Database → CoreLogic, Esri, HERE, TomTom and Apple), plus the
Franklin St name collision. The fix is to get **"N Fort Mason" recognized as the address of those exact points** at the
top of that chain, and then to push the correction into each downstream service.

## 2. Workstreams

### A. Evidence: one truth table, all sources (first)
For **every** Fort Mason residence and building (~25), record what each source says:
- **Address form:** USPS form (the deliverable address on mail and leases), City EAS, SF Assessor parcel situs,
  Census TIGER, OpenStreetMap, Overture.
- **Apple Maps forward:** search "3 Fort Mason" and note where the pin lands.
- **Apple Maps reverse:** "My Location" on site; note the address shown.
- **Google, HERE, TomTom, Mapbox and Esri:** forward lookup.
- **Delivery and rideshare apps:** a few real failures with screenshots (DoorDash, Uber Eats, Amazon, UPS, FedEx).

Output: `evidence/truth-table.md` plus screenshots. That one page makes every appeal easy to say yes to.

### B. Decide the canonical address (with the community)
- Settle what is *correct*: "N Fort Mason" (what USPS delivers to), the City's "N Franklin St / MacArthur Ave", or both
  with one as the official alias.
- The ask is probably: **keep the City's points, and add "N Fort Mason" as the official alias, landmark name or
  mailing address.** EAS already has `complete_landmark_name` and `landmark_aliases` fields; today they are empty here.
- Owners: residents, NPS / Golden Gate National Recreation Area (the landowner) and its housing office.

### C. Fix at the source, top of the chain first
1. **City of San Francisco addressing.** EAS is run by the Department of Technology's Enterprise GIS team; address
   assignment sits with Public Works mapping. Ask for the "N Fort Mason" alias or landmark on each point, and a ruling on
   the Franklin St collision. Escalate through the District 2 Supervisor's office if needed. This fix flows to
   911/dispatch, the Assessor, the National Address Database and, through them, the commercial vendors.
2. **OpenStreetMap.** Already right for the "N Fort Mason" form. Verify each building against the truth table, then add
   the City form as `alt_addr` (or the agreed tagging), so OSM-based services (Apple partly, Mapbox, Overture) get both.
   Anyone can edit; this one we can do ourselves.
3. **Census TIGER / National Address Database.** These update from the City's submissions. Confirm the path once
   item 1 lands.
4. **USPS.** Confirm the "N Fort Mason" records (ZIP+4, delivery point) are correct; that is what every address
   validator (CASS, Smarty, Loqate) checks against.

### D. Fix downstream, each service
- **Apple Maps:**
  - Coordinated "Report an Issue" submissions, one per address, from residents on site with the truth table attached.
  - Apple Business Connect for the Fort Mason organizations (NPS, Fort Mason Center).
  - A direct escalation path to the Apple Maps data team, through contacts or press, citing the government fix.
- **HERE, TomTom, Esri and Mapbox:** their public map-feedback tools, submitted from the truth table.
- **Delivery apps:** a saved-address and drop-off-notes workaround for residents now; feedback to their mapping teams
  once the upstream data is fixed.

### E. Verify and keep it fixed
Re-run `scripts/crosscheck.py` and the Apple and delivery spot checks monthly. Close the project when Apple (forward and
reverse) and the main delivery apps land every resident address on the right building.

## 3. What we need from residents
- The exact address form on mail, leases and USPS records for your home, and for 2–3 neighbours.
- 2–3 screenshots: Apple "My Location" at home, and Apple search for your address showing where the pin lands.
- One or two real delivery failures (app, date, where the driver went).
- Who's already involved: residents' group, NPS housing contact, and any past correspondence with Apple, the City or USPS.
