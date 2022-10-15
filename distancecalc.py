import requests
import json
from geopy import distance
from itertools import combinations
import time

with open("keys.txt", "r") as keys:
    keysString = keys.read()

keysArray = keysString.split("\n")
mapsKey = keysArray[0]
mbtaKey = keysArray[1]

with open("stations-full.json", "r") as stationsStream:
    stationsString = stationsStream.read()
stations = json.loads(stationsString)
allStations = stations.keys()

with open("stations.json") as stationsWithLinesStream:
    stationsWithLinesString = stationsWithLinesStream.read()
stationsWithLines = json.loads(stationsWithLinesString)
allLines = stationsWithLines.keys()

stationsWithLinesAndIds = {}

for line in allLines:
    for stop in stationsWithLines[line]:
        if not (line in stationsWithLinesAndIds):
            stationsWithLinesAndIds[line] = {}
        stationsWithLinesAndIds[line][stop["id"]] = stop

allPairs = list(combinations(allStations, 2))
index = 0
amt = len(allPairs)
removeError = 0
removeSameLine = 0
removeTooLong = 0

with open("allPairs.json", "w") as allPairsStream:
    allPairsStream.write(json.dumps(allPairs))

allPairsFull = allPairs[:]

for pair in allPairsFull:
    index += 1
    if (index%50 == 0): print (str(index) + "/" + str(amt))
    place1 = pair[0]
    place2 = pair[1]
    if("error" in stations[place1] or "error" in stations[place2]):
        allPairs.remove(pair)
        removeError += 1
        continue
    yeet = False
    for line in allLines:
        if((place1 in stationsWithLinesAndIds[line]) and (place2 in stationsWithLinesAndIds[line])): # tests if both stations are along the same line... mostly works
            allPairs.remove(pair)
            removeSameLine += 1
            yeet = True
            break
    if (yeet): continue # there HAS to be a better way than this but i cant figure it out for the life of me
    place1lat = stations[place1]["lat"]
    place1long = stations[place1]["long"]
    place2lat = stations[place2]["lat"]
    place2long = stations[place2]["long"]
    dist = distance.distance((place1lat, place1long), (place2lat, place2long)).miles
    if(dist > 1):
        allPairs.remove(pair)
        removeTooLong += 1
        continue

print("total length:" + str(len(allPairs)))
print("error: " + str(removeError))
print("same line: " + str(removeSameLine))
print("too long: " + str(removeTooLong))

with open("allPairs.json", "w") as out:
    out.write(json.dumps(allPairs, indent=4))
