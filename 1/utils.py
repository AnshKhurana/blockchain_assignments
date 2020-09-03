"""
Util functions and classes for both Seeds and Peers

Functions:
    - findSeeds()
    - getUnique(peers)

Classes:
    - Connection

"""

from enum import Enum


class socket_type(Enum):
    SELF = 1
    SEED = 2
    PEER = 3


class Connection(object):
    """
    Class to handle socket storage and interaction.
    When type is PEER, ip and port store the listening socket of the peer
    """

    def __init__(self, socket, ip=None, port=None, sock_type=socket_type.PEER):
        """Create Connection along with identity"""
        self.socket = socket
        self.ip = ip
        self.port = port
        self.type = sock_type
        self.sent_id = False  # used by peer to check if it needs to send listening port info

    def pretty(self):
        """Return ip and port info."""
        return (self.ip, self.port)


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
    return [peers[0]]
