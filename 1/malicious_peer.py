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
import datetime

encoding = 'utf-8'

# GLOBAL VARIABLES
PACKET_SIZE = 1024
MAX_CONNECTED_PEERS = 4
LIVENESS_DELAY = 13 # 13 seconds for each message

read_mask = selectors.EVENT_READ
read_write_mask = selectors.EVENT_READ | selectors.EVENT_WRITE

class Peer:
    def __init__(self):
        super().__init__()

        seeds = findSeeds()
        N = len(seeds)
        # select n//2+1 seeds randomly
        random.shuffle(seeds)
        self.seeds = seeds[:N//2+1]

        self.received_peer_list = []
        self.received_from = 0
        self.peers = []
        self.sel = selectors.DefaultSelector()
        
        self.listener_socket = socket(AF_INET, SOCK_STREAM)
        self.listener_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.listener_socket.bind(('', 0))
        self.listener_socket.listen(10)
        self.listener_socket.setblocking(False)
        self.listening_port = self.listener_socket.getsockname()[1]
        self.ip = self.listener_socket.getsockname()[0]
        
        self.sel.register(self.listener_socket, read_mask, data=Connection(
            self.listener_socket, '', self.listening_port, socket_type.SELF))

        self.seed_broadcast_queue = [] #Pending messages that must be broadcasted to all seeds connected with it

    def connect_with_seeds(self):
        # connect to the selected seeds
        for (ip, port) in self.seeds:
            s = socket(AF_INET, SOCK_STREAM)
            s.setblocking(False)
            print("connecting to seed", ip, ":", port)
            s.connect_ex((ip, port))
            self.sel.register(s, read_write_mask,
                        data=Connection(s, ip, port, sock_type=socket_type.SEED))

    def run(self):
        while True:
            events = self.sel.select(timeout=None)

            for key, mask in events:
                if key.data.type == socket_type.SELF: # accept a new connection
                    self.accept_peer(key.fileobj)
                elif key.data.type == socket_type.PEER: # receive a message from peer
                    self.service_peer(key, mask)
                elif key.data.type ==  socket_type.SEED: # receive/send a message from seed
                    self.service_seed(key, mask)

    def accept_peer(self, sock):
        """
        Accept connection from peer and add it to selector.
        Dont send peer list as we haven't received listening port yet
        """
        peer, (peer_ip, peer_port) = sock.accept()
        print("Received connection from", peer_ip, peer_port)
        peer.setblocking(False)
        self.sel.register(peer, read_write_mask,
                    data=Connection(peer, peer_ip, peer_port, socket_type.PEER))

    def connect_with_peers(self):
        
        if len(self.received_peer_list) == 0:
            print("No other peers in the network")

        peer_list = getUnique(self.received_peer_list)
        random.shuffle(peer_list)
        peer_list = peer_list[:min(len(peer_list), MAX_CONNECTED_PEERS)]

        for (ip, port) in peer_list:
            s = socket()
            s.setblocking(False)
            print("connecting to peer", ip, ":", port)
            s.connect_ex((ip, port))
            self.sel.register(s, read_write_mask,
                        data=Connection(s, ip, port, sock_type=socket_type.PEER))

        print("sent connection request to all")
        
    def service_seed(self, key, mask):
        """
        Handle all requests to/from seed.
        Cases:
            - We need to send listening port info to seed
            - Seed has sent peer list. Add it to local peer list,
            if n/2 seeds are registered, start connecting to other peers
        """
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            try:
                recv_data = sock.recv(PACKET_SIZE)
                if not recv_data:
                    print("closing connection to", data.ip, ":", data.port)
                    self.sel.unregister(sock)
                    sock.close()
                else:
                    rec = json.loads(recv_data.decode(encoding))
                    print("received peer list from",
                        data.ip, ":", data.port, ":", rec)
                    self.received_peer_list += rec
                    self.received_from += 1
                    if self.received_from == len(self.seeds):
                        print("Connecting to peers")
                        self.connect_with_peers()

            except Exception as e:
                print(e)
                self.sel.unregister(sock)
                sock.close()
        
        if mask & selectors.EVENT_WRITE:
            if not data.sent_id:  # Send listening port info
                print("sending listening info to", data.ip, ":", data.port)
                sock.sendall(json.dumps({'port': self.listening_port}).encode(encoding))
                data.sent_id = True
            for message in self.seed_broadcast_queue:
                if message not in data.sent_messages:
                    print("sending dead node message to", data.ip, ":", data.port, ":", message)
                    sock.sendall((message).encode(encoding))
                    data.sent_messages.append(message)

    def parse_peer_message(self, sock, data, message):

        print("received from peer", data.ip, ":", data.port, ":", message)
        if message.startswith("Liveness Request"):
            pass
        elif message.startswith("Liveness Reply"):
            # must update that the peer is active
            data.tries_left = MAX_TRIES

    def handle_dead_peer(self, sock, data):
        current_time = datetime.datetime.now(tz=None)
        message = "Dead Node_{}_{}_{}_{}".format(data.ip, data.port, current_time, self.ip)
        self.seed_broadcast_queue.append(message)
        print("closing connection to", data.ip, ":", data.port)
        self.sel.unregister(sock)
        sock.close()

    def service_peer(self, key, mask):
        """
        Handle all requests to/from peer.
        Cases:
            - A peer has sent listening port. Add it to connected peers
            - Handle gossip and liveness messages
        """
        sock = key.fileobj
        data = key.data
        current_time = datetime.datetime.now(tz=None)
        if mask & selectors.EVENT_READ:
            try:
                recv_data = sock.recv(PACKET_SIZE)  # Should be ready to read
                if not recv_data:
                    print("should close connection to", data.ip, ":", data.port, "in 3 tries")
                    # Currently commented out just to check the correctness of dead node reporting
                    print("closing connection to", data.ip, ":", data.port)
                    self.sel.unregister(sock)
                    sock.close()
                else:
                    self.parse_peer_message(sock, data, recv_data.decode(encoding))

            except Exception as e:
                print(e)
                self.sel.unregister(sock)
                sock.close()
        
        if mask & selectors.EVENT_WRITE:
            # check the time since the last liveness check
            if data.liveness_timestamp is None or current_time-data.liveness_timestamp>datetime.timedelta(seconds = LIVENESS_DELAY):
                if data.tries_left <= 0:
                    self.handle_dead_peer(sock, data)
                else:
                    message = "Liveness Request_{}_{}".format(current_time, self.ip)
                    print("sending liveness request to", data.ip, ":", data.port)
                    sock.sendall(message.encode(encoding))
                    data.liveness_timestamp = current_time
                    data.tries_left -= 1

if __name__ == "__main__":
    
    p = Peer()
    p.connect_with_seeds()
    p.run()
