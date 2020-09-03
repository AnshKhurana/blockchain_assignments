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

encoding = 'utf-8'

# GLOBAL VARIABLES
# max size of a message
PACKET_SIZE = 1024
NUM_MESSAGES = 10
MESSAGE_TIME = 5

class Peer:
    def __init__(self):
        super().__init__()

        # get seeds        
        seeds = findSeeds()
        N = len(seeds)
        # select n//2+1 seeds randomly
        random.shuffle(seeds)
        self.seeds = seeds[:N//2+1]

        self.received_peer_list = []
        self.received_from = 0
        self.peers = []
        self.sel = selectors.DefaultSelector()
        
        # set-up listening socket for the node.
        self.listener_socket = socket(AF_INET, SOCK_STREAM)
        # listens on a socket even if previously occupied
        self.listener_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        #debug : What is the IP it takes by default??
        self.listener_socket.bind(('', 0))
        self.listener_socket.listen(10)
        self.listener_socket.setblocking(False)
        self.listening_port = self.listener_socket.getsockname()[1]
        #debug : Below we are registering it with NULL ip address, take care
        self.sel.register(self.listener_socket, selectors.EVENT_READ, data=Connection(
            self.listener_socket, '', self.listening_port, socket_type.SELF))

    def connect_with_seeds(self):
        # connect to the selected seeds
        for (ip, port) in self.seeds:
            s = socket(AF_INET, SOCK_STREAM)
            s.setblocking(False)
            print("connecting to seed", ip, ":", port)
            s.connect_ex((ip, port))
            #debug : No need to do write here with selector below
            self.sel.register(s, selectors.EVENT_READ | selectors.EVENT_WRITE,
                        data=Connection(s, ip, port, sock_type=socket_type.SEED))

    def run(self):
        while True:
            events = self.sel.select(timeout=None)
            for key, mask in events:
                # debug: data is never None, change below line.
                if key.data.type==socket_type.SELF:
                    self.accept_peer(key.fileobj)
                else:
                    self.service_connection(key, mask)

    def accept_peer(self, sock):
        """
        Accept connection from peer and add it to selector.
        Dont send peer list as we haven't received listening port yet
        """
        # Haven't checked this function
        peer, (peer_ip, peer_port) = sock.accept()
        print("Received connection from", peer_ip, peer_port)
        peer.setblocking(False)
        #debug: Firstly confusion due to default arguments below, also incorrect initialization i guess.
        #debug: remove WRITE and check
        self.sel.register(peer, selectors.EVENT_READ | selectors.EVENT_WRITE,
                    data=Connection(peer, peer_ip, peer_port, socket_type.PEER))

    def connect_with_peers(self):
        
        if len(self.received_peer_list) == 0:
            print("No other peers in the network")

        for (ip, port) in getUnique(self.received_peer_list):
            s = socket()
            s.setblocking(False)
            print("connecting to peer", ip, ":", port)
            s.connect_ex((ip, port))
            #debug: selector WRITE remove
            self.sel.register(s, selectors.EVENT_READ | selectors.EVENT_WRITE,
                        data=Connection(s, ip, port, sock_type=socket_type.PEER))

        print("sent connection request to all?")

        
    def service_connection(self, key, mask):
        #debug: Do the first kind of message just after connecting, not here.
        """
        Handle all requests.
        Cases:
            - We need to send listening port info to seed
            - Seed has sent peer list. Add it to local peer list,
            if n/2 seeds are registered, start connecting to other peers
            - A peer has sent listening port. Add it to connected peers
            - Handle gossip and liveness messages
        """
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            try:
                recv_data = sock.recv(PACKET_SIZE)  # Should be ready to read
                if not recv_data:
                    print("closing connection to", data.ip, ":", data.port)
                    self.sel.unregister(sock)
                    sock.close()
                elif data.type == socket_type.SEED:  # get peer list
                    rec = json.loads(recv_data.decode(encoding))
                    print("received peer list from",
                        data.ip, ":", data.port, ":", rec)
                    self.received_peer_list += rec
                    self.received_from += 1
                    if self.received_from == len(self.seeds):
                        print("Connecting to peers")
                        self.connect_with_peers()
                elif data.type == socket_type.PEER:
                    print("received from peer", data.ip, ":", data.port, ":", recv_data)

            except Exception as e:
                print(e)
                self.sel.unregister(sock)
                sock.close()
        
        if mask & selectors.EVENT_WRITE:
            if data.type == socket_type.SEED and not data.sent_id:  # Send listening port info
                print("sending listening info to", data.ip, ":", data.port)
                sock.sendall(json.dumps({'port': self.listening_port}).encode(encoding))
                data.sent_id = True


if __name__ == "__main__":
    
    p = Peer()
    p.connect_with_seeds()
    p.run()
