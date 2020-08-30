"""
Util functions and classes for both Seeds and Peers

Functions:
    - findSeeds()
    - getUnique(peers)

Classes:
    - Connection

"""


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
    return peers


class Connection(object):
    """Class to handle socket storage and interaction."""

    def __init__(self, socket, ip, port):
        self.socket = socket
        self.ip = ip
        self.port = port

    def pretty(self):
        """Return ip and port info."""
        return {'ip': self.ip, 'port': self.port}
