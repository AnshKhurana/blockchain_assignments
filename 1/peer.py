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
import time
import os
import selectors
sel = selectors.DefaultSelector()

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


def accept_peer(sock):
    # Haven't checked this function
    peer, (peer_ip, peer_port) = sock.accept()
    print("Received connection from", peer_ip, peer_port)
    peer.setblocking(False)
    conn = Connection(peer, peer_ip, peer_port)
    sel.register(peer, selectors.EVENT_READ | selectors.EVENT_WRITE, data=conn)
    peer_list.append(conn)


def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(packet_size)  # Should be ready to read
        if recv_data:
            if data['type'] == 'seed':
                current_peers = json.loads(recv_data.decode(encoding))
                print("Peer list ", current_peers,
                      "from", data['conn'].pretty())

                # Add to own peer list,
                # Connect to new peers if not already connected to 4 peers
    if mask & selectors.EVENT_WRITE:
        pass


# connect to the selected seeds
for (ip, port) in seeds:
    s = socket()
    s.setblocking(False)
    e = s.connect_ex((ip, port))
    print("E", os.strerror(e))
    conn = Connection(s, ip, port)
    sel.register(s, selectors.EVENT_READ | selectors.EVENT_WRITE,
                 data={'type': 'seed', 'conn': conn})
    seed_list.append(conn)

while True:
    events = sel.select(timeout=None)
    for key, mask in events:
        if key.data is None:
            accept_peer(key.fileobj)
        else:
            service_connection(key, mask)
