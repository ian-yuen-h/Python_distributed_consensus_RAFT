import time
import requests
import sys
import json
from subprocess import Popen, PIPE, signal

PORTS = []
MESSAGE = "/message"
TOPIC = "/topic"
STATUS = "/status"

FOLLOWER = "Follower"
LEADER = "Leader"
CANDIDATE = "Candidate"
IP = "http://127.0.0.1:"
REQUEST_TIMEOUT = 1

def get_status(address):
    return requests.get(address + STATUS, timeout=REQUEST_TIMEOUT)

def wait_for_flask_startup(address):
    number_of_tries = 20
    for _ in range(number_of_tries):
        try:
            return requests.get(address)
        except requests.exceptions.ConnectionError:
            time.sleep(0.1)
    raise Exception('Cannot connect to server')

def main():
    global PORTS
    load_json()
    filepath = "../src/node.py"

    dict1 = {}

    for i in range(len(PORTS)):
        address = IP+str(PORTS[i])
        startup_sequence = ["python3",
                                    filepath,
                                    "./config_multiple.json",
                                    str(i)]
        string1 = "./src/databases/stdout_capture_part1_test_"+str(i)+".txt"
        f = open(string1, "w")                                 
        process = Popen(startup_sequence, stdout=f)
        dict1[PORTS[i]] = process
        time.sleep(1)
        wait_for_flask_startup(address)
    
    time.sleep(10)
    leaders = []
    for port in PORTS:
        address = IP+str(port)
        result = get_status(address)
        status = result.json()["role"]
        if status == "Leader":
            leaders.append(port)
    
    #only one leader
    assert (len(leaders) <=1)

    #kill leader
    dict1[leaders[0]].kill()
    PORTS.remove(leaders[0])
    time.sleep(10)

    for port in PORTS:
        address = IP+str(port)
        result = get_status(address)
        status = result.json()["role"]
        if status == "Leader":
            leaders.append(port)

    #reelection, only one leader
    assert (len(leaders) <=1)

    for each in dict1:
        dict1[each].kill()
    pass


def load_json():
    global PORTS
    file_path = "./config_multiple.json"

    with open(file_path) as f:
        ss = json.load(f)

    for i in range(len(ss["addresses"])):
        PORTS.append(ss["addresses"][i]["port"])
    

if __name__ == "__main__":
    main()