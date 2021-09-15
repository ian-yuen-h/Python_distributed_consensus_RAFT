Source: raft paper
Ongaro, Diego. Ousterhour, John. In Search of an Understandable Consensus Algorithm (Extended Version), 2014, USENIX


## Part 1: Single Node Message Queue
REST endpoints are implemented as per specification in node.py.
State Machine covers both the log and the message queue storage in persistant data storage (json files) which are named after the port where the node was established. All data are encoded as json files to ensure persistent storage and debugging ease.

The state.py module is established for every node created in order to allow for node rejoining persistence. The StateMachine class has attributes
```
self.name = name
self.load_database()
self.load_log()
self._currentTerm = 0
self.lock = threading.Lock()
self.leaderId = None
self.commitIndex = -1 
self.lastApplied = -1 
self.server_records = {}

self.log
self.queue
```
self.name: the port of a database which is used as its name

self.load_database(): a function defined in StateMachine used to load in the database if it has been saved, otherwise it creates an empty dictionary for the database and stores either into self.queue

self.load_log(): a function defined in StateMachine used to load in the log if it has been sabed for that node's name, otherwise it creates an empty dictionary for the log and stores either into self.log

self._currentTerm: initialized to zero, this term is updated when a follower becomes a candidate and increments their current term, or if a follower receives an appendRPC from a valid leader whose term is higher than their own

self.lock: this was used in debugging a horrid race condition (thanks Max) and is left as a warning for all who dare enter the world of distributed systems

self.leaderId: this attribute is initially set to None. When a node receives a valid appendRPC, the leaderId is updated

self.commitIndex: initialized to to -1 to account for python's list index beginning at 0, this index is established within method add_to_log. If the rpc is valid from a valid leader, the commitIndex is set in one of two methods:

- if the leader's commitIndex is greater than the node's commit index (such as when the leader has received a request rpc), the node's index is updated to be the minimum of the leader commitIndex and their own so the node can be caught up from their last matched location with the leader. 
- otherwise, the node is not behind and it does not need to change its own commitIndex

self.lastApplied: an integer which keeps track of the last index the node has applied to their own database. Whenever a node receives an appendRPC, the node checks if their commit index is greater than the lastApplied. If it is, the node increments their lastApplied and runs commit_to_database which commits the log[lastApplied] entry. 

The queue is stored as a dictionary where each key is a topic and each topic is formed as a list of messages. A GET request to message returns the 0th position message, a PUT topic creates a new key in the queue dictionary. A dictionary was chosen as it seemed the most logical decision when it came to storing multiple topics and adding messages to each of those topics.

When implemented, the log is designed as a list in order to allow for easy indexing. Each entry in the list is a dictionary of the form

```
{
    "action": str,
    "topic": str,
    "message": str,
    "term": str
}
```
where message is an optional addition if a client wishes to add a message to a topic. Otherwise, message is not included in the entry. The state.py has a function, commit_to_database, which commits the log entry of the lastApplied attribute.

An appendRPC is made in the form

```
{
    term: int
    leaderId (port): int
    prevLogIndex: int
    prevLogTerm: int
    entries: []
    leaderCommit: int
}
```
The appendRPC is made as discussed in the source listed above where the leader sends their currentTerm, their PORT (so that followers can forward requests to leaders), the previous log index which is the index of the leader's log entry immediately preceeding the incoming request, the leader's previous log term which is the term of the immediately preceding log entry, an entry array to allow for more than one item sent if the node is failry behind, and the leader's commit index so that the follower can check if they are up to date as described above in attributes.

#### REST endpoints

There are nine endpoints created.

1. /messages is a GET request used for debugging which returns the entire database of a node

2. / is a GET request which returns a welcome message and the specific node's port

3. /topic/ GET returns a list of topics

4. /topic/ PUT, POST takes in a message body {'topic': str} and returns {'success': True} if the topic does not exist and it has been created. Otherwise, it returns {'success': False}

5. /message/ PUT, POST takes in a message body {'topic': str, 'message': str} and returns {'success': True} if the topic exists and the message has been added successfully to the queue. Otherwise, it returns {'success': False}

6. /message/<topic> GET returns the 0th index position of the queue for that particular key, and returns {'success': True, 'message': str} if the topic exists and the message has been successfully retreived. Otherwise, it returns {'success': False}

7. /status/ GET returns {'role': TYPE, 'term': STATE.currentTerm}, the current role of the node and the term that the node believes to be in.

8. /appendRPC is a method used by the leader to send either a heartbeat (which is the exact same form as the appendRPC discussed above but has no entries) or new entries to all other ports. This route is accessed only by the nodes the leader sent to, and the nodes return {'success': True} if the term of the leader is greater than or equal to their own, and if the previous log index is either 0 or less than the current log of the follower and the leader and follower agree on term for the previous log. If the rpc is determined to be valid, the node restarts their election timeout. Otherwise, {'success': False}.

9. Finally, the request vote RPC (which is not used in this first part) takes an rpc of the form below and if the candidate has a term greater than the receiver, if the receiver has not voted for another node, and if the last log terms are agreeable, the receiver returns {'term': STATE.currentTerm, 'voteGranted': True} and ensures it is a follower. Otherwise, the receiver returns {'term': STATE.currentTerm, 'voteGranted': False}
```
{
    term: candidate's term
    candidateId: candidate name
    lastLogIndex: index of the candidate's last log entry
    lastLogTerm: term of the candidate's last log entry
}
```

Finally, the node.py stores a few global variables.

```
TYPE = 'follower'
HOST = "localhost"
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
```
These some global variables (such as the port, IP) are inputted using a json to run the testing suite. The others are standardized. All nodes begin as followers, all nodes have a randomized election timeout (TIMEOUT) between 1 and 2, all nodes start off having voted for no one, have a set thread timeout, and all nodes start a last_current_time counter so that the election function can determine the whether or not (given the current time) an election should be started.

For part 1, all but the election can be used. Initially, the leader could be set at node conception and the rest would be followers which eliminated any issue with part 1 elections or lack of a leader.

Part 1 was tested at length using postman in order to get and put messages and topics and to test the error handling of the system.

## Part 2: Leader Election Algorithm
All nodes begin as followers as indicated by the global variable type.

Election timeout is implemented in the function election_timeout in node.py as a difference check between global variable LAST_CURRENT_TIME (see updating last_current_time information above) and current time at checking. If difference exceed a randomly chosen time interval, timeout = True. If timeout is set to True, the main() while loop (which checks the status of timeout) runs the function start_election(). The timeout was decided in this manner as the work of maintaining a clock is then done by the operating system and the nodes themselves do not need to keep track of the time, they need only to mark their last current time and set their current time.

election_start() resets the timeout in order to allow for elections to time out and new elections to commence if such a situation arises where no node gets the majority of the votes.
At election start, the node transitions to a candidate, votes for themself, and updates their current term. Within the lastLogIndex and lastLogTerm (elements of the requestVoteRPC that will be sent out to all followers in the same manner as the appendEntriesRPC), there is are conditionals handling edge cases where the nodes have received no logs or the term is 0 (the first term) and the nodes have no logs storing previous term information. In this case, the values both default to zero. The candidate then marks themselves as having voted for themselves, preps an rpc as indicated in number nine of part 1,and calculates the votes needed for the candidate to move forward with their leadership (a strict majority). The candidate threads every request, keeps a list of every response that occured within a timeout (in order to ensure threads would not block), and then counts only success returns as votes. If the candidate gets all the votes they need and are still a candidate by this point, the candidate transitions to a leader and creatres (using the function server_record in the state.py module) a dictionary to keep track of every node;s match and next indices.

Threading was chosen to handle outgoign requests in order to ensure requests were made in parallel, and error handling was included to ensure threads returning to the join would not block one another if one were timing out but the thread were waiting for an indeterminate amount of time. Instead, if the thread takes too long, it is counted as a node not voting for the candidate. Finally, the start_election() includes logic that if a node has returned a result which is voteGranted = False and its term is greater than the candidate's term, the candidate transitions to a follower.

There are a few places of repeated logic which took place before a race condition was debugged. While many of the conditions are taken care of, there are likely edge cases which result in problematic returns due to duplicated logic.

In the main function, a while loop runs. If the type is leader, the node will send out heartbeats using the send_heartbeats() function. This function is creates an rpc (much like the leader does in the api enpoints) with no entries, sends them to all other nodes in the network known to it via the append_entries() function.

The append entries function includes some complicated logic handled here before it is sent to followers as the work is done by one node rather than many when the majority of the time. The function splits into two parts, heartbeat (length of append entries is 0) and entries (if the entries length are greater than 0).

Entries: If a leader wants to create an entry, there are two scenarios. First, the leader is the only node in netwrok. It can immediately update its commit index, and commit to its database as the leader has already added to its log in the api endpoints. Second, there are more than one node. The leader then must send an rpc to the /appendRPC route to every other port if the next index of the node is behind th eleader or if the match index of the port is behind by more than one for the leader's log. The leader implements a similar threading approach as the start_election() function. However, the leader additionally must make some checks.

- The if successful (as determined above in /appendRPC), the leader updates the server_records for that port's match index and next index
- if unsuccessful, the leader decrements the mext indicies and sends a new rpc to the same node until the last commit they agree upon is found.
- the leader then determines the largest index the majority of nodes agree on and sets that as the leader's commit index and commits to the database. 

The leader then responds to the client with the result of its own applied state. The logic is taken from the RAFT paper above with help on Flask debugging from Max.

HeartBeat: this is done so that the timeout is reset for every follower unless they don't hear from the leader.

Tests for this were initially run via postman to ensure that leaders are reelected when one crashes (run with 3 and 5 nodes) but if there are less than a majority present, no leader is elected.

## Part 3: Distributed Replication Model
Clients only interact with leaders.
If node contacted is not leader, the known leader port is returned as described in the endpoints.

# Leaders:
Threads handle appendRPC calls.
If response is True, log is appended successfully, logs and commits are up to date for that node. nextIndex, matchIndex are updated, port is noted down.
With a majority of ports including new log, the log entry is commited by the Leader.
If response is False, decrement nextIndex, recursively call append_entries.

# Nodes:
At every call to appendRPC route, checks if the purported leader has a lower term, returns False if so, for leader to update itself.
Checks if there is a new log item to add, and whether the previous log index term matches, ensuring that logs are in sync with leaders. Only then call add_to_log method in STATE.

Otherwise return False

# StateMachine/Log automation and methods:
add_to_log method is called after a particular append call passes conditional tests; begins with updating own term. Depending on if the entries arg is non-empty, non-empty being heartbeat thus only update terms if needed. If not append the entries to log.
Updates commitindex through last_applied field, given by leader, calls commit_to_database.

commit_to_database, using last_applied field, depending on log action, performs said action on the message queue, save to json. Includes topic checks, creating topic if one does not exist. does_topic_exist is a utility method that checks if a topic exists.

load_log, load_database; called on startup or after coming back from crash.

1. Fault Tolerance
Heartbeat messages are sent periodically to update timeout on nodes.
If timeout exceeds defined TIMEOUT, an election is called, ensuring that there will always be a leader.
Every message carries with it term information, ensuring that all nodes are aligned in terms of node.
Logs are only commited after getting a majority of successful log appendages. As discussed in part 2, leaders must not only get a mjaority of successful responses, but also ensure the responses are up to date concerning their nextIndex and matchIndex. 

The log replication is certainly the most lagging part of the project. There are occasions where nodes fail, once becoming leaders, to acheive requests from clients. This has been attempted to be handled with try/exepct and other error handling, but this is certainly by far the location for greatest improvement.

Fault tolerance was tested using postman (writing requests and put to the localhost:node/method# while running multiple nodes on the terminal) and the debugging and status methods specified in part 1 are used in order to ensure first, leaders are successfully elected and that their databases (using the /messages/ method) are replicated correctly. This process worked after extensive debugging with Max to remove the race condition.