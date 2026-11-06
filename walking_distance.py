"""Find walking distances and times between MBTA stations that are close to each other.

Run with `uv run walking_distance.py`. It:
1. Loads every station on a rail route or the Silver Line from the MBTA v3 API, plus the
   hypothetical Regional Rail stations in infill-stations.json, and writes them to stations.json.
2. Finds pairs of stations within MAX_CROW_FLIES_MI of each other that don't share a route.
3. Asks an OpenStreetMap walking router (OSRM, hosted by FOSSGIS) for the walking distance and time between each pair,
   reusing results from walking-distances.json when neither station has moved.
4. Writes the results to walking-distances.json.
"""

import argparse
import json
import math
import os
import time
from itertools import combinations

import requests

MBTA_API_URL = "https://api-v3.mbta.com"
# OSRM walking routes over OpenStreetMap, run for free by FOSSGIS. Their usage policy asks for at most one request a
# second and an identifying User-Agent: https://fossgis.de/arbeitsgruppen/osm-server/nutzungsbedingungen/
WALKING_TABLE_URL = "https://routing.openstreetmap.de/routed-foot/table/v1/driving/"
USER_AGENT = "station-walking-distance (https://github.com/transitmatters/station-walking-distance)"

# Light rail, heavy rail and Commuter Rail
RAIL_ROUTE_TYPES = "0,1,2"
SILVER_LINE_ROUTE_IDS = ["741", "742", "743", "746", "749", "751"]

MAX_CROW_FLIES_MI = 1.0
METERS_PER_MILE = 1609.344
EARTH_RADIUS_MI = 3958.8

STATIONS_FILE = "stations.json"
INFILL_STATIONS_FILE = "infill-stations.json"
WALKING_DISTANCES_FILE = "walking-distances.json"

# One request takes many destinations, so pairs are grouped by origin to make fewer requests
MAX_DESTINATIONS_PER_REQUEST = 25
SECONDS_BETWEEN_ROUTING_REQUESTS = 1.0
MAX_RATE_LIMIT_RETRIES = 5


def read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as file:
        return json.load(file)


def write_json(path, data):
    with open(path, "w") as file:
        json.dump(data, file, indent=4, sort_keys=True)
        file.write("\n")


def mbta_get(path, params):
    headers = {}
    api_key = os.environ.get("MBTA_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    while True:
        response = requests.get(MBTA_API_URL + path, params=params, headers=headers, timeout=30)
        # Without an API key, the MBTA API allows 20 requests a minute
        if response.status_code == 429:
            reset_at = int(response.headers.get("x-ratelimit-reset", time.time() + 10))
            time.sleep(max(1, reset_at - time.time()))
            continue
        response.raise_for_status()
        return response.json()["data"]


def load_route_ids():
    routes = mbta_get("/routes", {"filter[type]": RAIL_ROUTE_TYPES, "fields[route]": "long_name"})
    return [route["id"] for route in routes] + SILVER_LINE_ROUTE_IDS


def load_mbta_stations():
    stations = {}
    for route_id in load_route_ids():
        route_stations = mbta_get(
            "/stops",
            {
                "filter[route]": route_id,
                "filter[location_type]": "1",
                "fields[stop]": "name,latitude,longitude,wheelchair_boarding",
            },
        )
        for data in route_stations:
            attributes = data["attributes"]
            station = stations.setdefault(
                data["id"],
                {
                    "id": data["id"],
                    "name": attributes["name"],
                    "lat": attributes["latitude"],
                    "long": attributes["longitude"],
                    "wheelchair_boarding": attributes["wheelchair_boarding"],
                    "routes": [],
                },
            )
            station["routes"].append(route_id)
    return stations


def load_stations():
    stations = load_mbta_stations()
    for infill_station in read_json(INFILL_STATIONS_FILE, []):
        if infill_station["id"] not in stations:
            stations[infill_station["id"]] = infill_station
    return stations


def crow_flies_miles(a, b):
    lat_a, long_a, lat_b, long_b = map(math.radians, (a["lat"], a["long"], b["lat"], b["long"]))
    h = math.sin((lat_b - lat_a) / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin((long_b - long_a) / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def find_candidate_pairs(stations):
    pairs = []
    for id_1, id_2 in combinations(sorted(stations), 2):
        station_1, station_2 = stations[id_1], stations[id_2]
        # Riding is the way to get between stations on the same route
        if set(station_1["routes"]) & set(station_2["routes"]):
            continue
        if crow_flies_miles(station_1, station_2) <= MAX_CROW_FLIES_MI:
            pairs.append((id_1, id_2))
    return pairs


def location(station):
    return [station["lat"], station["long"]]


def query_walking_distances(origin, destinations):
    """Walking (distance in meters, time in seconds) from origin to each destination, or None if there's no route"""
    coordinates = ";".join(f"{station['long']},{station['lat']}" for station in [origin, *destinations])
    params = {
        "sources": "0",
        "destinations": ";".join(str(index + 1) for index in range(len(destinations))),
        "annotations": "distance,duration",
    }
    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
        response = requests.get(
            WALKING_TABLE_URL + coordinates, params=params, headers={"User-Agent": USER_AGENT}, timeout=60
        )
        if response.status_code != 429 or attempt == MAX_RATE_LIMIT_RETRIES:
            break
        time.sleep(2**attempt * 5)
    response.raise_for_status()
    body = response.json()
    if body["code"] != "Ok":
        raise RuntimeError(f"Walking route request failed: {body['code']} {body.get('message', '')}")
    walks = []
    for destination, distance_m, duration_s in zip(destinations, body["distances"][0], body["durations"][0]):
        if distance_m is None or duration_s is None:
            print(f"No walking route from {origin['id']} to {destination['id']}")
            walks.append(None)
        else:
            walks.append((round(distance_m), round(duration_s)))
    return walks


def group_by_origin(to_query):
    """Batches of (origin, [(pair_id, destination)]) small enough for one request each"""
    by_origin = {}
    for pair_id, station_1, station_2 in to_query:
        by_origin.setdefault(station_1["id"], (station_1, []))[1].append((pair_id, station_2))
    batches = []
    for origin, destinations in by_origin.values():
        for start in range(0, len(destinations), MAX_DESTINATIONS_PER_REQUEST):
            batches.append((origin, destinations[start : start + MAX_DESTINATIONS_PER_REQUEST]))
    return batches


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Update stations.json and report how many pairs need looking up, without looking them up",
    )
    args = parser.parse_args()

    stations = load_stations()
    write_json(STATIONS_FILE, stations)
    print(f"Loaded {len(stations)} stations")

    pairs = find_candidate_pairs(stations)
    previous = read_json(WALKING_DISTANCES_FILE, {})
    results = {}
    to_query = []
    for id_1, id_2 in pairs:
        pair_id = f"{id_1}_{id_2}"
        cached = previous.get(pair_id)
        station_1, station_2 = stations[id_1], stations[id_2]
        if cached and cached["location_1"] == location(station_1) and cached["location_2"] == location(station_2):
            # Accessibility changes more often than locations, so always take the latest
            cached["wheelchair_boarding_1"] = station_1["wheelchair_boarding"]
            cached["wheelchair_boarding_2"] = station_2["wheelchair_boarding"]
            results[pair_id] = cached
        else:
            to_query.append((pair_id, station_1, station_2))
    print(f"{len(pairs)} pairs within {MAX_CROW_FLIES_MI} mi, {len(to_query)} need looking up")

    if args.dry_run:
        return
    if to_query:
        batches = group_by_origin(to_query)
        for index, (origin, destinations) in enumerate(batches):
            walks = query_walking_distances(origin, [destination for _, destination in destinations])
            for (pair_id, destination), walk in zip(destinations, walks):
                if walk:
                    distance_m, duration_s = walk
                    results[pair_id] = {
                        "place1": origin["id"],
                        "place2": destination["id"],
                        "wheelchair_boarding_1": origin["wheelchair_boarding"],
                        "wheelchair_boarding_2": destination["wheelchair_boarding"],
                        "location_1": location(origin),
                        "location_2": location(destination),
                        "distance_m": distance_m,
                        "distance_mi": round(distance_m / METERS_PER_MILE, 3),
                        "duration_s": duration_s,
                    }
            # Save as we go, so a run cut short by a quota resumes where it stopped
            write_json(WALKING_DISTANCES_FILE, {**previous, **results})
            print(f"{index + 1}/{len(batches)} {origin['id']}: {len(destinations)} destinations")
            time.sleep(SECONDS_BETWEEN_ROUTING_REQUESTS)

    write_json(WALKING_DISTANCES_FILE, results)
    print(f"Wrote {len(results)} pairs to {WALKING_DISTANCES_FILE}")


if __name__ == "__main__":
    main()
