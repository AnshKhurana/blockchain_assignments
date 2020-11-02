"""
Util functions and classes for both Seeds and Peers

Functions:
    - findSeeds()
    - getUnique(peers)

Classes:
    - Connection

"""

from enum import Enum
import datetime
import selectors
import os
import time
import hashlib
import numpy as np
from queue import Queue

MAX_TRIES = 3  # maximum 3 timeouts for liveness testing
read_mask = selectors.EVENT_READ
read_write_mask = selectors.EVENT_READ | selectors.EVENT_WRITE
DEBUG_MODE = True # Change to false for submission

dead_node_msg = "Dead Node:{}:{}:{}:{}~"
listening_port_msg = "Listening Port:{}~"
liveness_request_msg = "Liveness Request:{}:{}:{}~"
liveness_reply_msg = "Liveness Reply:{}:{}:{}:{}:{}~"
gossip_msg = "{}:{}:{}~"

def find_sha3(message):
    hasher = hashlib.sha3_256()
    hasher.update(message.encode('utf-8'))
    return hasher.hexdigest()[-4:]

class Block(object):
    """ Class to handle one block """
    def __init__(self, block_string):
        [self.previous_hash, self.merkel_root, self.timestamp, self.level] = block_string.split('_')
        self.level = int(self.level)

    def __str__(self):
        return '_'.join([self.previous_hash, self.merkel_root, self.timestamp, str(self.level)])

    def sha3(self):
        # Don't include self.level while generating hash of block
        block_string = ''.join([self.previous_hash, self.merkel_root, self.timestamp])
        return find_sha3(block_string)

class Blockchain(object):
    """ Class to handle blockchain structure """
    def __init__(self):
        self.tree = {}
        self.max_level = 0
        self.genesis_hash = "9e1c"
        # block to mine on
        self.max_block_hash = self.genesis_hash
        
    def validate(self, block):
        block_time = int(block.timestamp)
        if block.previous_hash not in self.tree and block.previous_hash != self.genesis_hash:
            return False
        elif time.time() > block_time + 3600 or time.time() < block_time - 3600:
            return False
        else:
            return True

    def add(self, block):
        block_hash = block.sha3()
        if block_hash in self.tree:
            return
        self.tree[block_hash] = block
        if block.level > self.max_level:
            self.max_level = block.level
            self.max_block_hash = block_hash

class Miner(object):
    """ Class to handle the mining roles of a peer """
    def __init__(self, interarrival_time, percentage_hash_power, seed):
        self.node_lambda = percentage_hash_power / (100.0*interarrival_time)
        self.blockchain = Blockchain()
        self.pending_queue = Queue(maxsize = -1)
        np.random.seed(seed)

    def waiting_time(self):
        # Returns the value of waiting time
        return datetime.timedelta(seconds=np.random.exponential(1.0/self.node_lambda))

    def mine(self):
        # Generates block. This function is to be called when the waiting time expires
        timestamp = int(time.time())
        merkel_root = "0"*4
        level = self.blockchain.max_level + 1
        previous_hash = self.blockchain.max_block_hash
        block_string = '_'.join([previous_hash, merkel_root, str(timestamp), str(level)])
        block = Block(block_string)
        self.blockchain.add(block)
        return block_string

    def get_blocks_in_chain(self):
        block_strings = []
        block_hash = self.blockchain.max_block_hash
        while block_hash!= self.blockchain.genesis_hash:
            block = self.blockchain.tree[block_hash]
            block_strings.append(str(block))
            block_hash = block.previous_hash
        return block_strings[::-1]

    def add_to_pending_queue(self, block):
        self.pending_queue.put(block)

    def add_to_tree(self, block):
        if self.blockchain.validate(block):
            self.blockchain.add(block)

    def process_pending_queue(self):
        valid_block_strings = []
        while not self.pending_queue.empty():
            block = self.pending_queue.get()
            if self.blockchain.validate(block):
                self.blockchain.add(block)
                valid_block_strings.append(str(block))
        return valid_block_strings


class socket_type(Enum):
    SELF = 1
    SEED = 2
    PEER = 3


class Printer(object):
    """Class to handle printing to screen and file."""

    def __init__(self, seed_or_peer):
        """Print to a file named <pid>.output."""
        if seed_or_peer == 'SEED':
            filename = "SEED_"+str(os.getpid())+".output"
        else:
            filename = "PEER_"+str(os.getpid())+".output"
        self.file_obj = open(filename, "w")

    def print(self, msg, should_print=True):
        """
        Writes to screen and to file.
        Use second argument to specify if writing is conditional on debug mode
        """
        msg = msg.replace('~','')
        if should_print:
            print(msg)
            self.file_obj.write(msg+"\n")


class Connection(object):
    """
    Class to handle socket storage and interaction.
    When type is PEER, ip and port store the listening socket of the peer
    """

    def __init__(self, socket, ip, port, sock_type, listener_port=None):
        """Create Connection along with identity"""
        self.socket = socket
        self.ip = ip
        self.port = port
        self.type = sock_type
        # used by peer and seed both to check if it needs to send listening port info
        self.sent_id = False
        # used by seed to keep track of port at which peer is listening
        self.listener_port = listener_port
        # timestamp of the last liveness message sent on this socket
        self.liveness_timestamp = None
        # self.gossip_timestamp = None
        self.tries_left = MAX_TRIES
        self.sent_messages = []
        self.hashed_sent = []
        self.created_at = datetime.datetime.now(tz=None)

    def pretty(self):
        """Return ip and port info."""
        return (self.ip, self.listener_port)


def findSeeds():
    """Read the config file and return an array of all the seeds info."""
    file = open('config.txt', 'r')
    seeds = file.readlines()
    seed_info = []
    for seed in seeds:
        ip = seed.split(':')[0]
        port = int(seed.split(':')[1].replace('\n', ''))
        seed_info.append((ip, port))
    return seed_info


def getUnique(peers):
    """Remove duplicate from a list of peers."""
    peers = [(peer[0], peer[1]) for peer in peers]
    return list(set(peers))
