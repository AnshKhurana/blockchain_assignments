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
import networkx as nx
import matplotlib.pyplot as plt

MAX_TRIES = 3  # maximum 3 timeouts for liveness testing
read_mask = selectors.EVENT_READ
read_write_mask = selectors.EVENT_READ | selectors.EVENT_WRITE
DEBUG_MODE = True  # Change to false for submission
LIVENESS_DEBUG_MODE = False  # Change to false for submission
PRINT_FLOODS = False  # Change to false for submission

dead_node_msg = "Dead Node:{}:{}:{}:{}~"
listening_port_msg = "Listening Port:{}~"
liveness_request_msg = "Liveness Request:{}:{}:{}~"
liveness_reply_msg = "Liveness Reply:{}:{}:{}:{}:{}~"
block_msg = "{}~"
height_msg = "Height:{}~"
sync_complete_msg = "Sync Complete~"


def find_sha3(message):
    hasher = hashlib.sha3_256()
    hasher.update(message.encode('utf-8'))
    return hasher.hexdigest()[-4:]


class Block(object):
    """ Class to handle one block """

    def __init__(self, block_string):
        [self.previous_hash, self.merkel_root, self.timestamp, self.level] = block_string.split(
            '_')  # he might take objection on giving self.level as argument to block

        self.level = int(self.level)

    def __str__(self):
        return '_'.join([self.previous_hash, self.merkel_root, self.timestamp, str(self.level)])

    def sha3(self):
        # Don't include self.level while generating hash of block
        block_string = ''.join(
            [self.previous_hash, self.merkel_root, self.timestamp])
        return find_sha3(block_string)


class Blockchain(object):
    """ Class to handle blockchain structure """

    def __init__(self, draw, logfolder=None, is_mal=False):
        self.tree = {}
        self.is_mal = is_mal
        self.max_level = 0
        self.genesis_hash = "9e1c"
        self.my_block_hashs = set()
        # block to mine on
        self.draw = draw
        self.max_block_hash = self.genesis_hash
        self.filename = None

        if self.is_mal:
            self.db_name = "MAL_BLOCK_DB_"+str(os.getpid())+".output"
        else:
            self.db_name = "BLOCK_DB_"+str(os.getpid())+".output"

        if logfolder:
            self.db_name = os.path.join(logfolder, self.db_name)

        self.db_obj = open(self.db_name, "w")

        if draw:
            if self.is_mal:
                self.filename = "MAL_CHAIN_"+str(os.getpid())+".png"
            else:
                self.filename = "CHAIN_"+str(os.getpid())+".png"
            if logfolder:
                self.filename = os.path.join(logfolder, self.filename)

            self.chain = nx.Graph()

    def validate(self, block, mine_delay=None):
        if mine_delay is not None:
            mine_delay += datetime.timedelta(milliseconds=1)
        block_time = int(block.timestamp)
        if block.previous_hash not in self.tree and block.previous_hash != self.genesis_hash:
            return False
        elif time.time() > block_time + 3600 or time.time() < block_time - 3600:
            return False
        # additional level based check
        elif (block.previous_hash == self.genesis_hash and block.level != 1) or (block.previous_hash != self.genesis_hash and block.level != self.tree[block.previous_hash].level+1):
            return False
        else:
            return True

    def update_db(self, block):
        block_hash = block.sha3()
        is_mine = block_hash in self.my_block_hashs
        mine_string = "generated" if is_mine else "received"
        block_string = str(block)
        line_to_write = '_'.join([block_hash, block_string, mine_string])
        self.db_obj.write(line_to_write+'\n')

    def add(self, block):

        if not self.validate(block):
            return

        block_hash = block.sha3()
        if block_hash in self.tree:
            return
        self.tree[block_hash] = block

        if self.draw:
            plt.clf()
            self.chain.add_edge(str(block.previous_hash), str(block_hash))
            pos = nx.spectral_layout(self.chain)
            # pos = nx.spiral_layout(self.chain)
            # pos = nx.shell_layout(self.chain)
            nx.draw_networkx_nodes(self.chain, pos)
            nx.draw_networkx_nodes(self.chain, pos, nodelist=[
                                   "9e1c"], node_color="red")
            # nx.draw_networkx_labels(self.chain, pos)
            nx.draw_networkx_edges(self.chain, pos)
            # nx.draw(self.chain, with_labels=True)
            plt.savefig(self.filename)

        if block.level > self.max_level:
            self.max_level = block.level
            self.max_block_hash = block_hash

        self.update_db(block)

    def mark_my_own(self, block):
        block_hash = block.sha3()
        self.my_block_hashs.add(block_hash)

    # def __del__(self):
    #     self.db_obj.close()


class Miner(object):
    """ Class to handle the mining roles of a peer """

    def __init__(self, interarrival_time, percentage_hash_power, draw, logfolder, is_mal):
        self.node_lambda = percentage_hash_power / (100.0*interarrival_time)
        self.blockchain = Blockchain(draw, logfolder, is_mal)
        self.pending_queue = Queue(maxsize=-1)
        # np.random.seed(seed)

    def waiting_time(self):
        # Returns the value of waiting time
        return datetime.timedelta(seconds=np.random.exponential(1.0/self.node_lambda))

    def mine(self, malicious=False):
        # Generates block. This function is to be called when the waiting time expires
        merkel_root = "0"*4
        level = self.blockchain.max_level + 1
        if malicious:
            previous_hash = "0"*4
            timestamp = np.random.randint(1e10, 1e11-1)
        else:
            timestamp = int(time.time())
            previous_hash = self.blockchain.max_block_hash
        block_string = '_'.join(
            [previous_hash, merkel_root, str(timestamp), str(level)])
        block = Block(block_string)

        if not malicious:
            self.blockchain.mark_my_own(block)

        self.blockchain.add(block)

        # adding blocks that are my own

        return block_string, block.sha3()

    def get_blocks_in_chain(self):
        block_strings = []
        block_hash = self.blockchain.max_block_hash
        while block_hash != self.blockchain.genesis_hash:
            block = self.blockchain.tree[block_hash]
            block_strings.append(str(block))
            block_hash = block.previous_hash
        return block_strings[::-1]

    def add_to_pending_queue(self, block, send_not_ip, send_not_port):
        self.pending_queue.put((block, send_not_ip, send_not_port))

    def add_to_tree(self, block, mine_delay=None):
        if self.blockchain.validate(block, mine_delay):
            self.blockchain.add(block)

    def process_pending_queue(self, mine_delay=None):
        valid_block_strings = []
        while not self.pending_queue.empty():
            block, send_not_ip, send_not_port = self.pending_queue.get()
            if self.blockchain.validate(block, mine_delay):
                self.blockchain.add(block)
                valid_block_strings.append(
                    (str(block), send_not_ip, send_not_port))
        return valid_block_strings


class socket_type(Enum):
    SELF = 1
    SEED = 2
    PEER = 3


class Printer(object):
    """Class to handle printing to screen and file."""

    def __init__(self, seed_or_peer, logfolder=None, is_mal=False):
        """Print to a file named <pid>.output."""
        if seed_or_peer == 'SEED':
            filename = "SEED_"+str(os.getpid())+".output"
        else:
            if is_mal:
                filename = "MAL_PEER_"+str(os.getpid())+".output"
            else:
                filename = "PEER_"+str(os.getpid())+".output"

        if logfolder:
            filename = os.path.join(logfolder, filename)

        self.file_obj = open(filename, "w")

    def print(self, msg, should_print=True):
        """
        Writes to screen and to file.
        Use second argument to specify if writing is conditional on debug mode
        """
        msg = msg.replace('~', '')
        if should_print:
            print(msg)
            self.file_obj.write(msg+"\n")

    # def __del__(self):
    #     self.file_obj.close()


class Connection(object):
    """
    Class to handle socket storage and interaction.
    When type is PEER, ip and port store the listening socket of the peer
    """

    def __init__(self, socket, ip, port, sock_type, listener_port=None, to_flood=False):
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

        self.tries_left = MAX_TRIES
        self.sent_messages = []
        self.hashed_sent = []
        self.created_at = datetime.datetime.now(tz=None)
        self.delayed_queue = []

        # Height sent by this peer
        self.k = -1
        self.sent_k = True
        self.to_flood = to_flood
        self.last_flooded = datetime.datetime.now(tz=None)

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


def check_and_make_dir(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
