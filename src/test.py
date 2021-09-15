import json
import sys

file_path = sys.argv[1]
index = sys.argv[2]

PORTS = []
PORT = 0
IP = None

def load_json():
    global PORT, PORTS, IP
    file_path = sys.argv[1]
    index = int(sys.argv[2])
    print("index", index)

    with open(file_path) as f:
        ss = json.load(f)

    for i in range(len(ss["addresses"])):

        if i == index:
            PORT= ss["addresses"][i]["port"]
            IP = ss["addresses"][i]["ip"]
        
        PORTS.append(ss["addresses"][i]["port"])

load_json()

print(PORT, IP)
print(PORTS)