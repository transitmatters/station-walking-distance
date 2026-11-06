# station-walking-distance
Finding walking distances and times between train stations.

[Regional Rail Explorer](https://github.com/transitmatters/regional-rail-explorer) uses these to plan journeys that leave one station and walk to another, like Lansdowne to Kenmore. The [schedule generator](https://github.com/transitmatters/regional-rail-schedule-generator) turns them into GTFS transfers.

## Setup
- [uv](https://docs.astral.sh/uv/) and Python 3.14 (`mise install` reads `.python-version`)
- `MBTA_API_KEY` (optional): an [MBTA v3 API](https://api-v3.mbta.com) key. Without one, the script waits out the 20 requests a minute limit, which takes about two minutes.

## Running
```bash
uv run walking_distance.py --dry-run   # Update stations.json and count the pairs to look up
uv run walking_distance.py             # Look up walking distances and update walking-distances.json
```

The script:
1. Loads every station on a light rail, subway, Commuter Rail or Silver Line route from the MBTA v3 API, plus the hypothetical Regional Rail stations in `infill-stations.json`. It writes them to `stations.json`.
2. Finds every pair of stations within 1 mile of each other as the crow flies that don't share a route.
3. Asks [OSRM](https://project-osrm.org/)'s walking profile over OpenStreetMap, hosted for free by [FOSSGIS](https://routing.openstreetmap.de/), for the walking distance and time between each pair's coordinates. A pair is only looked up again if one of its stations moved.
4. Writes the results to `walking-distances.json`. Each run refreshes wheelchair accessibility from the MBTA API.

No API key or billing is needed. A full run looks up about 450 station pairs, grouped by origin into about 150 requests sent one a second, per FOSSGIS's [usage policy](https://fossgis.de/arbeitsgruppen/osm-server/nutzungsbedingungen/). If walking times look wrong for a station, the fix is usually in OpenStreetMap's footpaths near it.

To add a hypothetical station, put it in `infill-stations.json` with its coordinates and the routes it's on.

## Output
`walking-distances.json` is keyed by the two station ids, sorted and joined with `_`. For example:
```json
{
    "place-WML-0025_place-kencl": {
        "place1": "place-WML-0025",
        "place2": "place-kencl",
        "wheelchair_boarding_1": 1,
        "wheelchair_boarding_2": 1,
        "location_1": [42.347581, -71.099974],
        "location_2": [42.348949, -71.095169],
        "distance_m": 607,
        "distance_mi": 0.377,
        "duration_s": 486
    }
}
```

`wheelchair_boarding` uses the [GTFS values](https://gtfs.org/documentation/schedule/reference/#stopstxt): `1` is accessible, `2` is not, and `0` is unknown. The times are for walking at about 5 km/h, not for wheelchairs, and don't include getting to and from the platform. Add a buffer before using them for routing.

## Linting
```bash
uv run ruff check . && uv run ruff format --check .
```
