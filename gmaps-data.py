import requests
import json
from urllib.parse import quote
import time


with open("keys.txt", "r") as keys:
    keysString = keys.read()

keysArray = keysString.split("\n")
mapsKey = keysArray[0]
mbtaKey = keysArray[1]

with open("allPairs.json", "r") as allPairsStream:
    allPairsString = allPairsStream.read()
allPairs = json.loads(allPairsString)

with open("stations-full.json", "r") as stationsFullStream:
    stationsFullString = stationsFullStream.read()
stationsFull = json.loads(stationsFullString)

url = "https://maps.googleapis.com/maps/api/distancematrix/json?mode=walking&origins={}&destinations={}&units=imperial&key={}"

finalout = {}

for pair in allPairs:
    place1 = {
        "id": pair[0],
        "address": stationsFull[pair[0]]["address"],
        "lat": stationsFull[pair[0]]["lat"],
        "long": stationsFull[pair[0]]["long"],
        "wheelchair_boarding": stationsFull[pair[0]]["wheelchair_boarding"]
    }
    place2 = {
        "id": pair[1],
        "address": stationsFull[pair[1]]["address"],
        "lat": stationsFull[pair[1]]["lat"],
        "long": stationsFull[pair[1]]["long"],
        "wheelchair_boarding": stationsFull[pair[1]]["wheelchair_boarding"]
    }
    pairIdList = [place1["id"], place2["id"]] # every pair has an id, place-123_place-234, ordered by .sort()
    pairIdList.sort()
    pairId = "_".join(pairIdList)
    place1["origin"] = place1["address"] if place1["address"] != None else str(place1["lat"]) + "," + str(place1["long"])
    place2["origin"] = place2["address"] if place2["address"] != None else str(place2["lat"]) + "," + str(place2["long"])
    thisUrl = url.format(quote(place1["origin"]), quote(place2["origin"]), mapsKey)
    if (pairId not in finalout):
        finalout[pairId] = {}
        req = requests.get(thisUrl)
        data = json.loads(req.text)
        distance = data["rows"][0]["elements"][0]["distance"]["text"]
        duration = data["rows"][0]["elements"][0]["duration"]["text"]
        if(float(distance.split(" ")[0]) > 1.5):
            place1["origin"] = str(place1["lat"]) + "," + str(place1["long"])
            place2["origin"] = str(place2["lat"]) + "," + str(place2["long"])
            thisUrl = url.format(quote(place1["origin"]), quote(place2["origin"]), mapsKey)
            req = requests.get(thisUrl)
            data = json.loads(req.text)
            distance = data["rows"][0]["elements"][0]["distance"]["text"]
            duration = data["rows"][0]["elements"][0]["duration"]["text"]
        finalout[pairId] = {
            "place1": place1["id"],
            "place2": place2["id"],
            "wheelchair_boarding_1": place1["wheelchair_boarding"],
            "wheelchair_boarding_2": place2["wheelchair_boarding"],
            "distance": distance,
            "duration": duration
        }
    print(place1["id"] + ", " + place2["id"])
    print(distance + ", " + duration)
    print()
    time.sleep(1)

with open("final-dist-and-time.json", "w") as finalStream:
    finalStream.write(json.dumps(finalout, indent=4))




# req = requests.get(url)