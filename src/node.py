import sys
from flask import Flask, app, request, Response
import requests
sys.path.append("src/")
from state import StateMachine
import json
import threading
import time
import random

## Global Variables Capitalized by Convention##
TYPE = 'follower'
HOST = "localhost"# will be sys.argv[0
# PORT = sys.argv[1]
# NAME = str(int(PORT)-5000)
# STATE = StateMachine(NAME, PORT)
# PORTS = [5000, 5001, 5002] 
PORTS = []
STATE = None
PORT = None
NAME = None
IP = None
THREAD_TIMEOUT = 1

LAST_CURRENT_TIME = time.time()
TIMEOUT = (random.randrange(1,2))
votedFor = None

APP = Flask(__name__)

## this is for debugging ##
@APP.route("/messages", methods = ["GET"])
def return_all_messages():

    return({"Database": NAME, "All messages: ": STATE.queue})

@APP.route("/", methods = ["GET"])
def welcome_to_server():
    return(f"Welcome to node {NAME}, in a server written by Christina and Ian!")

@APP.route("/topic/", methods = ["PUT", "POST"])
def create_topic():
    """Client sends a request to make a topic to the specific port.
    The client's request is in the format:
    
    {'topic': str}

    When the leader receives this request, the leader sends an appendRPC with
    the information:

        {
            term: leader’s term
            leaderId (port): follower can redirect clients
            prevLogIndex: index of leader's log entry immediately preceding incoming
            prevLogTerm: term of leader's prevLogIndex entry
            entries []: array with log entries to store (empty for heartbeat)
            leaderCommit: leader's commitIndex
        }
    to all nodes it knows are in the system.

    """
    if TYPE == "Leader":
        topic = request.json['topic']
        does_topic_exist = STATE.does_topic_exist(topic)
        if does_topic_exist == True:
            return json.dumps({'success': False})

        if len(STATE.log) > 0:
            prev_index = len(STATE.log)-1
            prev_term = STATE.log[prev_index]['term']
        else: 
            prev_index = 0
            prev_term = 0

        to_append = {'term': STATE.currentTerm,
                    'leaderId': PORT,
                    'prevLogIndex': prev_index,
                    'prevLogTerm': prev_term,
                    'entries': [{'action': 'add', 'topic': topic, 'term': STATE.currentTerm}],
                    'leaderCommit': STATE.commitIndex}

        STATE.add_to_log(to_append)
        result = append_entries(to_append)

        return result
    else:
        return json.dumps({'success': False})

@APP.route("/topic/", methods = ["GET"])
def get_topics():
    if TYPE == "Leader":
        topic_list = list(STATE.queue.keys())
        return({'success': True, 'topics': topic_list})
    else:
        return json.dumps({'success': False})

@APP.route("/message/", methods = ["PUT", "POST"])
def put_message():
    if TYPE == "Leader":
        topic = request.json['topic']
        message = request.json['message']
        if STATE.does_topic_exist == False:
            return json.dumps({'success': False})

        if len(STATE.log) > 0:
            prev_index = len(STATE.log)-1
            prev_term = STATE.log[prev_index]['term']
        else: 
            prev_index = 0
            prev_term = 0

        to_append = {
                    'term': STATE.currentTerm,
                    'leaderId': PORT,
                    'prevLogIndex': prev_index,
                    'prevLogTerm': prev_term,
                    'entries': [{'action': 'add', 'topic': topic, 'message': message,'term': STATE.currentTerm}],
                    'leaderCommit': STATE.commitIndex
                    }
        
        STATE.add_to_log(to_append)
        result = append_entries(to_append)
        return result
    else:
        return json.dumps({'success': False})
@APP.route("/message/<topic>/", methods = ["GET"])
def get_message(topic):
    if TYPE == "Leader":
        if STATE.does_topic_exist == False:
            return json.dumps({'success': False})
        try:
            if len(STATE.queue[topic]) == 0:
                return json.dumps({'success': False})
        except KeyError:
            return json.dumps({'success': False})

        if len(STATE.log) > 0:
            prev_index = len(STATE.log)-1
            prev_term = STATE.log[prev_index]['term']
        else: 
            prev_index = 0
            prev_term = 0

        to_append = {
                    'term': STATE.currentTerm,
                    'leaderId': PORT,
                    'prevLogIndex': prev_index,
                    'prevLogTerm': prev_term,
                    'entries': [{'action': 'remove', 'topic': topic, 'term': STATE.currentTerm}],
                    'leaderCommit': STATE.commitIndex
                    }

        STATE.add_to_log(to_append)
        result = append_entries(to_append)
        print(result)
        return result

    else: 
        return json.dumps({"success": False})
        
@APP.route("/status/", methods = ['GET'])
def get_status():
    return {'role': TYPE, 'term': STATE.currentTerm}

@APP.route("/appendRPC", methods = ["POST"])
def inter_nodal_communication():
    """
        {
          leader is sending the rpc, of form 
            term: leader’s term
            leaderId (port): follower can redirect clients
            prevLogIndex: index of leader's log entry immediately preceding incoming
            prevLogTerm: term of leader's prevLogIndex entry
            entries []: array with log entries to store (empty for heartbeat)
            leaderCommit: leader's commitIndex
        }
    """
    global TYPE, votedFor
    rpc = request.json

    if rpc['term'] < STATE.currentTerm:
        return {'term': STATE.currentTerm, 'success': False, 'port': PORT}

    if (rpc['prevLogIndex'] == 0) or (rpc['prevLogIndex'] < len(STATE.log) and STATE.log[rpc['prevLogIndex']]['term'] == rpc['prevLogTerm']):
        global LAST_CURRENT_TIME
        LAST_CURRENT_TIME = time.time()

        STATE.add_to_log(rpc)

        return {'term': STATE.currentTerm, 'success': True, 'port': PORT}

    return {'term': STATE.currentTerm, 'success': False, 'port': PORT}

@APP.route("/requestVoteRPC/", methods = ['POST', 'PUT'])
def requestVoteRPC():
    """
    Candidates send an rpc of the form:
        {
            term: candidate's term
            candidateId: candidate name
            lastLogIndex: index of the candidate's last log entry
            lastLogTerm: term of the candidate's last log entry
        }

    return: {term: currentTerm, voteGranted: bool}
        voteGranted:   
            False if the term if term < currentTerm
            False if votedFor != null or candidateId
            True if votedFor is null or candidateId AND the lastLogIndex is >= receiver log index
    """
    global votedFor, LAST_CURRENT_TIME
    rpc = request.json

    if rpc['term'] < STATE.currentTerm:
        return json.dumps({'term': STATE.currentTerm, 'voteGranted': False})
    
    if votedFor in [None, rpc['candidateId']]:
        if len(STATE.log) > 0:
            receiver_last_index = len(STATE.log) - 1
            receiver_last_term = STATE.log[len(STATE.log) - 1]['term']
        else: 
            receiver_last_index = 0
            receiver_last_term = 0

        if (rpc['lastLogTerm'] > receiver_last_term) or (rpc['lastLogTerm'] == receiver_last_term and rpc['lastLogIndex']>=receiver_last_index):
            votedFor = rpc['candidateId']
            global TYPE
            TYPE = 'follower'
            LAST_CURRENT_TIME = time.time()
            return json.dumps({'term': STATE.currentTerm, 'voteGranted': True})
    return json.dumps({'term': STATE.currentTerm, 'voteGranted': False})

def append_entries(rpc):
    """
    AppendEntries is a function which only the leader should have access to.
    The leader sends this out as part of the heart beat.
    There are two responses the leader can receive: success or failure

    Failures:

        Node is not up to date
        Node cannot be contacted
        Node takes too long to reply to the leader
        Node has a higher term

    If success: no action required
    If fail: the leader and follower must find out what is the last 
        entry in the log that the follower and leader agree on?
        Leader decrements the follower log # by 1, and and sends an RPC
            if the follower agrees with it, (success) the leader sends
            from that index onward all the indices the follower is missing
            if fail, keep decrementing
    """
    if TYPE == 'Leader':
        if len(rpc['entries']) > 0:
            threads_list = []
            results = []
            if len(PORTS)==1:
                N=STATE.commitIndex
                Nprev = N +1
                STATE.commitIndex = Nprev
                STATE.lastApplied += 1
                result = STATE.commit_to_database()
                return result   

            for port in PORTS:
                if port != int(PORT) and (STATE.server_records[str(port)]['nextIndex'] < len(STATE.log) or
                    STATE.server_records[str(port)]['matchIndex'] < len(STATE.log) - 1):
                        
                    url = f"http://127.0.0.1:{port}/appendRPC"
                    t1 = threading.Thread(target=send_internodal_message, args=(url, rpc, results))
                    threads_list.append(t1)
                    t1.start() 
                    
            
            for thread in threads_list:
                thread.join(timeout = THREAD_TIMEOUT)

            for result in results:
                if result.json()['success'] == True:
                    port = result.json()['port']
                    STATE.server_records[str(port)]['nextIndex'] = len(STATE.log)
                    STATE.server_records[str(port)]['matchIndex'] = len(STATE.log) - 1

                else:
                    port = result.json()['port']
                    STATE.server_records[str(port)]['nextIndex'] -= 1
                    prev_index = STATE.server_records[str(port)]['nextIndex'] - 1
                    prev_term = STATE.log[prev_index]['term']

                    rpc['entries'].insert(0, STATE.log[prev_index+1])
                    rpc['prevLogIndex'] = prev_index
                    rpc['prevLogTerm'] = prev_term
                    rpc['leaderCommit'] = STATE.commitIndex

                    append_entries(rpc)      
            try:
                N = min([STATE.server_records[str(port)]['matchIndex'] for port in PORTS if port != int(PORT)])
                Nprev = N
            except:
                N=STATE.commitIndex
                Nprev = N +1
                if STATE.does_topic_exist(rpc["entries"][0]["topic"]):
                    return {"success": False}
                else:
                    STATE.commitIndex = Nprev
                    STATE.lastApplied += 1
                    result = STATE.commit_to_database()
                    return result

            for n in range(N, len(STATE.log)-1):
                N = max(
                    sum([0 if STATE.server_records[str(port)]['matchIndex'] < n else 1 for port in PORTS if port != int(PORT)]),
                    N
                )
                if N < len(PORTS)//2 + 1:
                    break
                Nprev = N

            print(STATE.server_records)
            for port in PORTS:
                if port != int(PORT):
                    print(STATE.server_records[str(port)]['nextIndex'])
            if Nprev > STATE.commitIndex: #and STATE.log[Nprev]['term'] == STATE.currentTerm
                STATE.commitIndex = Nprev
                STATE.lastApplied += 1
                result = STATE.commit_to_database()

                return result 
            return {"success": False} ######
        
        else: 
            results = []
            for port in PORTS:
                if port != int(PORT):
                    url = f"http://127.0.0.1:{port}/appendRPC"
                    t1 = threading.Thread(target=send_internodal_message, args=(url, rpc, results))
                    t1.start() 

def send_internodal_message(url, jason, results):
    try:
        res = requests.post(url, json = jason, timeout=THREAD_TIMEOUT)
        if res.status_code == 200:
            results.append(res)
    except:
        pass

def send_heartbeats():
    if len(STATE.log) > 0:
        prev_index = len(STATE.log)-1
        prev_term = STATE.log[prev_index]['term']
    else: 
        prev_index = 0
        prev_term = 0
    to_append = {'term': STATE.currentTerm,
                'leaderId': PORT,
                'prevLogIndex': prev_index,
                'prevLogTerm': prev_term,
                'entries': [],
                'leaderCommit': STATE.commitIndex}
    append_entries(to_append)

def election_timeout():
    """
    checks if current time, has interval, larger than randomly selected number
    if so, then time-outed, return True
    if not, return False
    """
    global votedFor
    votedFor = None

    current_time = time.time()
    timed_out = False

    if current_time - LAST_CURRENT_TIME > TIMEOUT:
        timed_out = True
    return timed_out

def start_election():
    
    global TYPE
    TYPE = "candidate"

    global LAST_CURRENT_TIME
    LAST_CURRENT_TIME = time.time()

    votes = 1 

    if len(STATE.log) > 0:
        lastLogIndex = len(STATE.log)-1
    else: lastLogIndex = len(STATE.log)

    if len(STATE.log) > 0:
        lastLogTerm = STATE.log[len(STATE.log)-1]['term']
    else: lastLogTerm = 0

    STATE.currentTerm += 1

    global votedFor
    votedFor = PORT

    rpc = {
            "term": STATE.currentTerm,
            "candidateId": PORT,
            "lastLogIndex": lastLogIndex,
            "lastLogTerm": lastLogTerm
            }
    needed = len(PORTS)//2 + 1 

    threads_list = []
    results = []

    for port in PORTS:
        if port != int(PORT):
            url = f"http://{HOST}:{port}/requestVoteRPC/"
            t1 = threading.Thread(target=send_internodal_message, args=(url, rpc, results))
            t1.start()      
            threads_list.append(t1)  

        for thread in threads_list:
            thread.join(timeout = THREAD_TIMEOUT)
        
        for result in results:
            if result.json()['voteGranted'] == True:
                votes += 1
            else:
                if result.json()['term'] > STATE.currentTerm:
                    TYPE = 'follower'
                    return 

    if votes >= needed:
        if TYPE == 'candidate':
            print(PORT,"is now the leader")
            TYPE = 'Leader'
            STATE.server_record(PORTS, PORT) 

def main():
    while True:
        if TYPE == 'Leader':
            send_heartbeats()
        elif TYPE != 'Leader' and election_timeout():
            start_election() 
        time.sleep(1) 
            
def run_flask():
    APP.run(host=HOST, port = PORT, debug=False)

def load_json():
    global PORT, PORTS, IP, STATE, NAME
    file_path = sys.argv[1]
    index = int(sys.argv[2])

    with open(file_path) as f:
        ss = json.load(f)

    for i in range(len(ss["addresses"])):

        if i == index:
            PORT= ss["addresses"][i]["port"]
            IP = ss["addresses"][i]["ip"]
        
        PORTS.append(ss["addresses"][i]["port"])

if __name__ == "__main__":
    load_json()
    NAME = str(int(PORT)-5000)
    STATE = StateMachine(NAME, PORT)
    t1 = threading.Thread(target=run_flask)
    t1.start()
    main()

IP = None
