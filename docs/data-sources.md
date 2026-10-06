# Data sources

Where addresses come from, who owns each source, whether this repo may republish it, and how to get it corrected.
**Rule of thumb:** open government and OpenStreetMap data can live in the repo, with attribution. Commercial map
services (Apple, Google, HERE, TomTom, Esri, Mapbox) can't be bulk-copied under their terms, so for those we record
**observations**: what a person saw, when, ideally with a screenshot.

## A. Authoritative / open sources (republishable)

| Source | What it holds for an address | Owner | License | In repo as | How a fix happens |
|---|---|---|---|---|---|
| **SF Enterprise Addressing System (EAS)** — DataSF `3mea-di5p` (base) and `ramy-di5m` (with units) | The City's official address points; also landmark-name and alias fields | City and County of SF, Dept of Technology Enterprise GIS; assignment through Public Works mapping | DataSF open data (ODC PDDL; check per dataset) | extracts in `data/`, refreshed by the scripts | Request to City addressing, with District Supervisor support. Flows to 911, the Assessor and the national address database |
| **SF Assessor parcels** (DataSF parcel datasets) | Parcel situs address; likely the path into CoreLogic, which Apple credits | SF Assessor-Recorder | DataSF open data (check) | to add | Through the Assessor, usually following EAS |
| **US Census TIGER address ranges + Census geocoder** | Street segments with number ranges; the fallback for most geocoders | US Census Bureau (updates from local governments) | US federal, public domain | geocoder results in `data/` | Updates from the City's submissions to the Census Bureau's address programmes |
| **National Address Database (NAD)** | National address points, contributed by states and counties | US DOT | public (check) | to add | Updates as the City and county contribute |
| **OpenStreetMap** | Community address tags on buildings; already right for the "N Fort Mason" form | OSM contributors | **ODbL 1.0** (attribution + share-alike) | extracts in `data/` | **We edit it directly**, following OSM tagging norms and the local community |
| **OpenAddresses** | Aggregated government address points | OpenAddresses community | each source keeps its own licence | to add | Fix the government source, and it re-ingests |
| **Overture Maps — addresses theme** | Open address layer used by members (Amazon, Meta, Microsoft, TomTom, Esri…) | Overture Maps Foundation | depends on the source (check per release) | to add | Fix the upstream source (OSM, government), and it re-ingests |
| **NPS building inventory** | Federal building numbers for park sites (Fort Mason, Presidio, Fort Baker, Marin Headlands) | National Park Service / GGNRA | US federal, public domain (check) | to add | NPS / GGNRA facilities |

## B. Services (observations only)

| Service | Who uses it | What we record | Where a fix is filed |
|---|---|---|---|
| **Apple Maps** (search and "My Location" reverse geocoding) | iPhone, Siri, CarPlay; many iOS apps through MapKit | Forward: where the pin lands for the address people use. Reverse: the address shown at the door. Date, iOS version, screenshot | In Maps, **Report an Issue**; Apple Business Connect for organisations; escalation once government data is fixed. Apple credits OSM, CoreLogic parcels, the US Census Bureau, USGS and Esri federal datasets |
| **Google Maps / Google Maps Platform** | Many delivery and rideshare apps | Same as Apple | Google Maps **Suggest an edit / fix an address** |
| **HERE** | Fleet and logistics routing, in-car navigation | Same, from HERE WeGo | HERE map feedback |
| **TomTom** | In-car navigation, logistics, Overture member | Same | TomTom MapShare / map feedback |
| **Esri World Geocoder** | Local government, 911 dispatch vendors | Same, from the ArcGIS geocoder | Esri community maps / feedback |
| **Mapbox** | Some delivery and logistics apps | Same | Mapbox feedback |
| **USPS** | Mail; every CASS address validator (Smarty, Loqate, Melissa) | Self-reported **mailing-address form** only; no bulk ZIP+4 data | USPS (local post office / district addressing) |
| **Delivery apps** (Amazon, UPS, FedEx, DoorDash, Uber Eats, Instacart…) | Drivers | Field reports: the address entered, where the driver went, photo, date | The company's support, quoting the upstream fix |

## C. People (private; never committed raw)

Neighbours' anecdotes are the most persuasive evidence and the most sensitive. Raw reports stay **private**. The public
repo gets only consented, de-identified observations: address, service, what happened, date. No names, phone numbers
or delivery photos showing people.
