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

MAX_TRIES = 3 # maximum 3 timeouts for liveness testing

class socket_type(Enum):
    SELF = 1
    SEED = 2
    PEER = 3


class Connection(object):
    """
    Class to handle socket storage and interaction.
    When type is PEER, ip and port store the listening socket of the peer
    """

    def __init__(self, socket, ip, port, sock_type):
        """Create Connection along with identity"""
        self.socket = socket
        self.ip = ip
        self.port = port
        self.type = sock_type
        self.sent_id = False  # used by peer and seed both to check if it needs to send listening port info
        self.listener_port = None # used by seed to keep track of port at which peer is listening
        self.liveness_timestamp = None #timestamp of the last liveness message sent on this socket
        # self.gossip_timestamp = None
        self.tries_left = MAX_TRIES
        self.sent_messages = []
        self.hashed_sent = []
        

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
