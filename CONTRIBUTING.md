# Contributing

Thanks for joining the Fort Mason Address Challenge. Read [CHALLENGE.md](CHALLENGE.md) for the goal and the rules.

## Good first contributions
- **Add a map system to the scoreboard** (`scripts/scoreboard.py`): reverse geocoding ("My Location"), HERE, TomTom,
  Esri, Mapbox. Keys are read from environment variables; never commit them.
- **Prove a root cause:** trace one wrong answer to its upstream source, with evidence anyone can re-run.
- **Add a stranded neighbourhood** to `data/areas.json` and run `python3 scripts/stranded.py <area-id>`.
- **Confirm reference locations** in `data/truth/fort-mason.csv` (set `verified_by_resident` to `yes`, if you live
  there or have checked on site).

## Ground rules
- Every claim comes with a re-runnable command or a dated screenshot.
- Legitimate channels only: no spam, no fake accounts, no automated mass reports.
- OpenStreetMap edits follow OSM norms. Discuss bulk changes with the local community first.
- No personal information about residents: names, phone numbers, photos of people.
- Say whether AI helped, and how. A human signs off on anything sent to an outside organisation.

## Running it
Python 3.10+, standard library only:

```
python3 scripts/crosscheck.py      # Fort Mason: City vs OSM vs Census
python3 scripts/scoreboard.py      # rebuild SCOREBOARD.md
python3 scripts/build_lookup.py    # data for the "Where does it send you?" tool
python3 scripts/build_site.py      # rebuild site/index.html
python3 scripts/stranded.py        # stranded-address detector for data/areas.json
```
