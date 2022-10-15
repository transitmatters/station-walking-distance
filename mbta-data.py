import requests
import json
import time

mbtaUrl = "https://api-v3.mbta.com"
with open("keys.txt", "r") as keys:
    keysString = keys.read()

keysArray = keysString.split("\n")
mapsKey = keysArray[0]
mbtaKey = keysArray[1]

stationsJSON = ""

with open("stations-info.json", "r") as stationsfile:
    stationsJSON = stationsfile.read()

stations = json.loads(stationsJSON)
allStations = stations.keys()

index = 0

for station in allStations:
    req = requests.get(mbtaUrl + "/stops/" + station + "?api_key=" + mbtaKey)
    reqData = req.json()
    if "errors" in reqData:
        stations[station]["error"] = reqData["errors"][0]["status"] + ": " + reqData["errors"][0]["title"]
        print(reqData["errors"][0]["status"] + ": " + reqData["errors"][0]["title"])
    else:
        stations[station]["wheelchair_boarding"] = reqData["data"]["attributes"]["wheelchair_boarding"]
        stations[station]["address"] = reqData["data"]["attributes"]["address"]
        stations[station]["lat"] = reqData["data"]["attributes"]["latitude"]
        stations[station]["long"] = reqData["data"]["attributes"]["longitude"]

    print(str(index) + ": " + stations[station]["id"] + " - " + stations[station]["name"])
    index += 1

    time.sleep(2)

output = json.dumps(stations, indent = 4)

with open("stations-full.json", "w") as stationsOutput:
    stationsOutput.write(output)

print("done!")



