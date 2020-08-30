"""
Usage: python peer.py 
TODO add custom config path

Peer Script. Connects to at least half the seeds randomly and gets peer list
Sends 10 example messages. Sends heartbeat every 13 seconds
"""

from socket import *
from utils import *
import random
import json

encoding = 'utf-8'

# max size of a message
packet_size = 1024
num_messages = 10
message_time = 5

seeds = findSeeds()
N = len(seeds)
# select n//2+1 seeds randomly
random.shuffle(seeds)
seeds = seeds[:N//2+1]

seed_list = []
peer_list = []
peers = []

# connect to the selected seeds
for (ip, port) in seeds:
    s = socket()
    s.connect((ip, port))
    seed_list.append(Connection(s, ip, port))
    # Receive the information about its current peers from the seed
    current_peers = json.loads(s.recv(packet_size).decode(encoding))
    # Can receive itself??
    print("Peer list", current_peers)
    peers = peers + current_peers

# select a max of 4 distinct peers to connect to
peers = getUnique(peers)
peers = peers[:min(4, len(peers))]

while True:
    pass
# connect to the selected peers
# for (ip, port) in peers:
#     s = socket()
#     s.connect((ip, port))
#     peer_list.append(Connection(s, ip, port))
