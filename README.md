# basic info
Python 3.10.5

`keys.txt` should contain the MBTA v3 API key on line 1, and the Google Maps API key on line 2.

# files in order of execution
## `more-station-info.py`
Converts `stations.json` with format:
```json
    {
        "Line": [
            {
                "id": "place-1234",
                "name": "Example Place"
            },
            ...
        ],
        ...
    }
```
into `stations-info.json` with format:
```json
    {
        "place-1234": {
            "id": "place-1234",
            "name": "Example Place"
        },
        ...
    }
```
## `mbta-data.py`
Converts `stations-info.json` into `stations-full.json`. It uses the MBTA v3 API to get the address, geographic coordinates, **and wheelchair accessibility** of each station.
``` json
{
    "place-1234": {
        "id": "place-1234",
        "name": "Example Place",
        "wheelchair_boarding": 1,
        "address": "100 Example Rd, Boston, MA, 02121",
        "lat": 12.345678,
        "long": -87.654321
    },
    ...
}
```
## `distance-calc.py`
Uses *GeoPy* to find all pairs of stations that are less than one mile apart as the crow flies. This uses coordinates and a rough calculation, but it narrows down the options by a *lot* so that minimal requests have to be made to the Google Maps API. It outputs `allPairs.json` with the format:
``` json
[
    [
        "place-1234",
        "place-exmpl"
    ],
    ...
]
```
## `gmaps-data.py`
Requests the walking distances and times between all pairs of stations from `allPairs.json`, and saves them to `final-dist-and-time.json`. The keys in the output file are named as `"place-exmpl_place-1234"`, with the two stations ordered by Python's `.sort()`. The format is as follows:
``` json
{
    "place-exmpl_place-1234": {
        "place1": "place-1234",
        "place2": "place-exmpl",
        "wheelchair_boarding_1": 1,
        "wheelchair_boarding_2": 0,
        "distance": "0.8 mi",
        "duration": "17 mins"
    },
    ...
}
```

