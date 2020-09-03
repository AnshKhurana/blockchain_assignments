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
received_from = 0
peers = []

listener_socket = socket(AF_INET, SOCK_STREAM)
# listens on a socket even if previously occupied
listener_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
listener_socket.bind(('', 0))
listener_socket.listen(10)
listener_socket.setblocking(False)
listening_port = listener_socket.getsockname()[1]
sel.register(listener_socket, selectors.EVENT_READ, data=Connection(
    listener_socket, '', listening_port, socket_type.SELF))


def accept_peer(sock):
    """
    Accept connection from peer and add it to selector.
    Dont send peer list as we haven't received listening port yet
    """
    # Haven't checked this function
    peer, (peer_ip, peer_port) = sock.accept()
    print("Received connection from", peer_ip, peer_port)
    peer.setblocking(False)
    sel.register(peer, selectors.EVENT_READ | selectors.EVENT_WRITE,
                 data=Connection(peer, peer_ip, None))


def service_connection(key, mask):
    """
    Handle all requests.
    Cases:
        - We need to send listening port info to seed
        - Seed has sent peer list. Add it to local peer list,
          if n/2 seeds are registered, start connecting to other peers
        - A peer has sent listening port. Add it to connected peers
        - Handle gossip and liveness messages
    """
    global received_peer_list, received_from
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        try:
            recv_data = sock.recv(packet_size)  # Should be ready to read
            if not recv_data:
                print("closing connection to", data.ip, ":", data.port)
                sel.unregister(sock)
                sock.close()
            elif data.type == socket_type.SEED:  # get peer list
                rec = json.loads(recv_data.decode(encoding))
                print("received peer list from",
                      data.ip, ":", data.port, ":", rec)
                received_peer_list += rec
                received_from += 1
                if received_from == len(seeds):
                    print("Connecting to peers")
                    for (ip, port) in getUnique(received_peer_list):
                        s = socket()
                        s.setblocking(False)
                        print("connecting to peer", ip, ":", port)
                        s.connect_ex((ip, port))
                        sel.register(s, selectors.EVENT_READ | selectors.EVENT_WRITE,
                                     data=Connection(s, ip, port, sock_type=socket_type.PEER))
            elif data.type == socket_type.PEER:
                print("received from peer", data.ip,
                      ":", data.port, ":", recv_data)
        except Exception as e:
            print(e)
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if not data.sent_id:  # Send listening port info
            print("sending listening info to", data.ip, ":", data.port)
            sock.sendall(json.dumps({'port': listening_port}).encode(encoding))
            data.sent_id = True


# connect to the selected seeds
for (ip, port) in seeds:
    s = socket()
    s.setblocking(False)
    print("connecting to seed", ip, ":", port)
    s.connect_ex((ip, port))
    sel.register(s, selectors.EVENT_READ | selectors.EVENT_WRITE,
                 data=Connection(s, ip, port, sock_type=socket_type.SEED))


while True:
    events = sel.select(timeout=None)
    for key, mask in events:
        if key.data is None:
            accept_peer(key.fileobj)
        else:
            service_connection(key, mask)
