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

def put_message(address, topic: str, message: str):
        data = {"topic": topic, "message": message}
        return requests.put(address + MESSAGE, json=data,  timeout=REQUEST_TIMEOUT)

def get_message(address, topic: str):
    return requests.get(address + MESSAGE + '/' + topic,  timeout=REQUEST_TIMEOUT)

def create_topic(address, topic: str):
    data = {"topic": topic}
    return requests.put(address + TOPIC, json=data, timeout=REQUEST_TIMEOUT)

def get_topics(address):
    return requests.get(address + TOPIC, timeout=REQUEST_TIMEOUT)

def get_status(address):
    return requests.get(address + STATUS, timeout=REQUEST_TIMEOUT)


def main():
    load_json()
    address = IP+str(PORTS[0])
    topic = "Greetings"
    message = "hola amigo"
    message2 ="hello world"
    filepath = "../src/node.py"
    startup_sequence = ["python3",
                                 filepath,
                                 "./config.json",
                                 "0"]
    string1 = "./src/databases/stdout_capture_part1_test"+".txt"
    f = open(string1, "w")                                 
    process = Popen(startup_sequence, stdout=f)
    
    time.sleep(2)

    result = create_topic(address, topic)
    assert result.json() == {"success": True}

    result = get_topics(address)
    assert result.json() == {"success": True, "topics": [topic]}

    result = put_message(address, topic, message)
    assert result.json() == {"success": True}

    result = put_message(address, topic, message2)
    assert result.json() == {"success": True}

    #fake topic
    result = put_message(address, "smooth", message)
    assert result.json() == {"success": False}

    #dequeueing message in correct order
    result = get_message(address, topic)
    assert result.json() == {"success": True, "message": message}

    result = get_message(address, topic)
    assert result.json() == {"success": True, "message": message2}

    #empty pop
    result = get_message(address, topic)
    assert result.json() == {"success": False}

    #wrong topic pop
    result = get_message(address, "smooth")
    assert result.json() == {"success": False}

    process.kill()
    pass


def load_json():
    global PORTS
    file_path = "./config.json"

    with open(file_path) as f:
        ss = json.load(f)

    for i in range(len(ss["addresses"])):
        PORTS.append(ss["addresses"][i]["port"])
    

if __name__ == "__main__":
    main()