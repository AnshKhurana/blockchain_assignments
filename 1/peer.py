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
received_peer_list = []
peers = []


def accept_peer(sock):
    # Haven't checked this function
    peer, (peer_ip, peer_port) = sock.accept()
    print("Received connection from", peer_ip, peer_port)
    peer.setblocking(False)
    conn = Connection(peer, peer_ip, peer_port)
    sel.register(peer, selectors.EVENT_READ | selectors.EVENT_WRITE, data=conn)
    peer_list.append(conn)


def service_connection(key, mask, recv_count):
    global received_peer_list
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(packet_size)  # Should be ready to read
        if recv_data:
            if data['type'] == 'seed':
                current_peers = json.loads(recv_data.decode(encoding))
                received_peer_list += current_peers
                recv_count+=1
                print("Peer list ", current_peers,
                      "from", data['conn'].pretty())
                # return recv_count
                # Add to own peer list,
                # Connect to new peers if not already connected to 4 peers
    if mask & selectors.EVENT_WRITE:
        pass
    return recv_count

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
    received_list_from = 0
    events = sel.select(timeout=None)
    for key, mask in events:
        if key.data is None:
            # accept_peer(key.fileobj)
            # not accepting peer connections until receving peer list from all seeds
            continue
        else:
            # print("event from seed")
            received_list_from = service_connection(key, mask, received_list_from)
    # print("received list from", received_list_from)
    if received_list_from == len(seeds):
        break

# registration done.
# connect with peers now.

print(received_peer_list)
selected_peers = random.choices(received_peer_list, k=min(len(received_peer_list), 4)) 
print(selected_peers)
# send request to every peer
if len(selected_peers) > 0:
    
    for peer_connection in selected_peers:
        ip = peer_connection['ip']
        port = peer_connection['port']
        print("trying to connect with", ip, port)
        s = socket()
        s.setblocking(False)
        e = s.connect_ex((ip, port))
        print("E", os.strerror(e))
        conn = Connection(s, ip, port)
        sel.register(s, selectors.EVENT_READ | selectors.EVENT_WRITE,
                 data={'type': 'peer', 'conn': conn})
                
# listen for requests from other peers
print("listening for connections now")
while True:
    events = sel.select(timeout=None)
    for key, mask in events:
        if key.data is None:
            # key.data['type'] == 'peer': ?
            accept_peer(key.fileobj)
        else:
            print(key.data)
            continue
            print("unexpected message from seed?")
            