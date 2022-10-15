import json
import copy

with open("final-dist-and-time.json", "r") as stream:
    finalString = stream.read()
final = json.loads(finalString)
pairids = final.keys()

for pair in pairids:
    final[pair]["distance_mi"] = float(final[pair]["distance"].split(" ")[0])
    final[pair]["duration_s"] = 60*int(final[pair]["duration"].split(" ")[0])
    final[pair].pop("distance")
    final[pair].pop("duration")

with open("final-dist-and-time-fixed.json", "w") as writestream:
    writestream.write(json.dumps(final, indent = 4))


