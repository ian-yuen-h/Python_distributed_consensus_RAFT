import json
import threading
from pathlib import Path
import os

class StateMachine:
    """
    The state machine stores the log, to which orders are appended
    before they are committed, and the database, which stores
    committed informations.
    """

    def __init__(self, name, port):
        """[summary]

        Args:
            name ([type]): [description]
        """
        self.name = name
        self.load_database() # stored as self.queue
        self.load_log() # stored as self.log
        self._currentTerm = 0
        self.lock = threading.Lock()
        self.leaderId = None
        self.commitIndex = -1 # initialize commitIndex
        self.lastApplied = -1 # initiate last applied
        self.server_records = {}

    @property
    def currentTerm(self):
        self.lock.acquire()
        c = self._currentTerm
        self.lock.release()
        return c

    @currentTerm.setter
    def currentTerm(self, value):
        self.lock.acquire()
        self._currentTerm = value
        self.lock.release()

    def load_log(self):
        """
        Function attempts to load in a file by the name of the node.
        If the file does not exist, the log is initiated as an empty
        list.

        """
        try:
            with open(f'src/databases/{self.name}log.json', "r") as fopen:
                self.log = json.load(fopen)
        except:
            self.log = []
            with open(f'src/databases/{self.name}log.json', "w") as fopen:
                json.dump(self.log, fopen, indent=4)

    def load_database(self):
        try:
            with open(f'src/databases/{self.name}queue.json', "r") as fopen:
                self.queue = json.load(fopen)
        except Exception:
            self.queue = {}
            # cwd = os.getcwd()
            # print(cwd)
            with open(f'src/databases/{self.name}queue.json', "w+") as fopen:
                json.dump(self.queue, fopen, indent=4)

    def commit_to_database(self):
        log_entry = self.log[self.lastApplied]

        if log_entry['action'] == 'remove':
            topic = log_entry['topic']
            message_popped = self.queue[topic].pop(0)
            with open(f'src/databases/{self.name}queue.json', "w") as fopen:
                json.dump(self.queue, fopen, indent=4)
            return json.dumps({'success': True, 'message': message_popped})
        else:
            topic = log_entry['topic']
            try:
                log_entry['message']
                result = self.does_topic_exist(topic)
                if result == False:
                    # return {'success': False, 'message': f"No such topic {topic} exists."}
                    return {"success": False}
                self.queue[topic].append(log_entry['message'])
                with open(f'src/databases/{self.name}queue.json', "w") as fopen:
                    json.dump(self.queue, fopen, indent=4)
                return json.dumps({'success': True})
            except:
                self.queue[topic] = []
                with open(f'src/databases/{self.name}queue.json', "w") as fopen:
                    json.dump(self.queue, fopen, indent=4)
                return json.dumps({'success': True})
                
    def does_topic_exist(self, topic):
        try: 
            self.queue[topic]
            return True
        except:
            return False

    def add_to_log(self, rpc):
        """This function is first called by the leader in order to add to the follower
        logs. This is what is called in append entries. Responses are measured in 
        threads from this function. Takes in a dictionary of the form:
        
        {
            term: leader’s term
            leaderId (port): follower can redirect clients
            prevLogIndex: index of leader's log entry immediately preceding incoming
            prevLogTerm: term of leader's prevLogIndex entry
            entries []: array with log entries to store (empty for heartbeat)
            leaderCommit: leader's commitIndex
        }

        Responses are returned of the form:

        {
            'term': currentTerm,
            'success': bool
        }

        Entries are written to the log are not commited, and do not update the database.
        The leader writes to their log before sending out appendEntriesRPC to followers
        with the log(s) to append. When the leader has received a majority of responses,
        the leader writes the entry to the database. The leader then notifies the other
        nodes that it is safe to commit the latest log, and followers execute the command
        of the latest log.
        """
        self.leaderId = rpc['leaderId']

        if len(rpc['entries']) > 0:
            del self.log[rpc['prevLogIndex']+1:]

            for entry in rpc['entries']:
                self.log.append(entry)
                print("added entry to log")

            with open(f'src/databases/{self.name}log.json', "w") as fopen:
                json.dump(self.log, fopen, indent=4)

        else:
            self.currentTerm = rpc['term']
            self.leaderId = rpc['leaderId']

        if rpc['leaderCommit'] > self.commitIndex:
            self.commitIndex = min(rpc['leaderCommit'], len(self.log)-1)

        if self.commitIndex > self.lastApplied:
            self.lastApplied += 1
            self.commit_to_database()

        return {'term': self.currentTerm, 'success': True}

    def server_record(self, ports, leader_port):
        """Function to be only called when the election is turned over in 
        order to keep track of the each server's nextIndex and matchIndex.
        
        Returns a dictionary of the form:
        {'Port': {'nextIndex': #, 'matchIndex': #} }
        which the node must maintain
        """
        servers = {}
        for port in ports:
            if port != int(leader_port):
                servers[str(port)] = {'nextIndex': len(self.log), 'matchIndex': 0}
        self.server_records = servers