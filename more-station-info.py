import json

with open("stations.json", "r") as linesStationsStream:
    linesStationsString = linesStationsStream.read()
linesStations = json.loads(linesStationsString)
lines = linesStations.keys()

stations = {}

for line in lines:
    stationsOfLine = linesStations[line]
    print(line)
    print(stationsOfLine)
    print()
    for station in stationsOfLine:
        if(station["id"] not in stations):
            stations[station["id"]] = {
                "id": station["id"],
                "name": station["name"]
            }

stationsJson = json.dumps(stations, indent=4)
with open("stations-info.json", "w") as infoStream:
    infoStream.write(stationsJson)

print("done")