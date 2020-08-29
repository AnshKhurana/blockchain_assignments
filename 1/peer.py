# code for peer when it wants to set up a TCP connection with a seed.

from socket import *
from utils import Connection, findSeeds
import random
import json

encoding = 'utf-8'

# max size of a message
packet_size = 1024

seeds = findSeeds()
N = len(seeds)
#select n//2+1 seeds randomly
random.shuffle(seeds)
seeds = seeds[:N//2+1]

seed_list = []
peers = []

for (ip, port) in seeds:
    s = socket()
    s.connect((ip, port))
    seed_list.append(Connection(s, ip, port))
    #Receive the information about its current peers from the seed
    current_peers = json.loads(s.recv(packet_size).decode(encoding))
    print("Peer list", current_peers)
    peers = peers + current_peers
    