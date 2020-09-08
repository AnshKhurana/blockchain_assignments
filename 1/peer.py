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
from hashlib import sha256

encoding = 'utf-8'

# GLOBAL VARIABLES
PACKET_SIZE = 1024
MAX_CONNECTED_PEERS = 4
LIVENESS_DELAY = 13  # 13 seconds for each message
GOSSIP_DELAY = 5  # send a message every 5 seconds
GOSSIP_SEND_LIMIT = 10  # send only 10 messages


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
        self.peer_list = []
        self.closed_sockets = []
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

        # Pending messages that must be broadcasted to all seeds connected with it
        self.seed_broadcast_queue = []
        self.start_making = False
        # timestamp of the last gossip message sent by this peer
        self.gossip_timestamp = None
        self.gossip_sent = 0
        self.message_list = dict()
        self.peer_broadcast_queue = []

        self.printer = Printer()

    def connect_with_seeds(self):
        # connect to the selected seeds
        for (ip, port) in self.seeds:
            s = socket(AF_INET, SOCK_STREAM)
            s.setblocking(False)
            self.printer.print(f"connecting to seed {ip}:{port}")
            s.connect_ex((ip, port))
            self.sel.register(s, read_write_mask,
                              data=Connection(s, ip, port, sock_type=socket_type.SEED))

    def run(self):
        while True:

            # make gossip message and push
            current_time = datetime.datetime.now(tz=None)
            if self.gossip_sent < GOSSIP_SEND_LIMIT and self.start_making:
                if self.gossip_timestamp is None or (current_time-self.gossip_timestamp) > datetime.timedelta(seconds=GOSSIP_DELAY):
                    message = gossip_msg.format(
                        current_time, self.ip, self.gossip_sent)
                    # None, None -> no constraint when sending your own
                    self.peer_broadcast_queue.append((message, None, None))
                    self.gossip_sent += 1
                    self.gossip_timestamp = current_time
                    # Does this need to be printed?
                    self.printer.print(
                        f"Generated my own gossip message: {self.gossip_sent}")

            # Try to reconnect to closed sockets
            for data in self.closed_sockets:
                # check the time since the last liveness check
                if data.liveness_timestamp is None or current_time-data.liveness_timestamp > datetime.timedelta(seconds=LIVENESS_DELAY):
                    if data.tries_left <= 0:
                        self.handle_dead_peer(data.socket, data)
                        self.closed_sockets.remove(data)
                    else:
                        try:
                            data.socket = socket()
                            data.socket.setblocking(False)
                            self.printer.print(
                                f"Trying to reconnect to peer {data.ip}:{data.port}")
                            data.socket.connect_ex((data.ip, data.port))
                            message = liveness_request_msg.format(
                                current_time, self.ip)
                            self.printer.print(
                                f"Sending liveness request to {data.ip}:{data.port}", DEBUG_MODE)
                            data.socket.sendall(message.encode(encoding))
                        except:
                            self.printer.print(
                                f"failed to send liveness request to {data.ip}:{data.port}", DEBUG_MODE)
                        data.liveness_timestamp = current_time
                        data.tries_left -= 1

            events = self.sel.select(timeout=None)

            for key, mask in events:
                if key.data.type == socket_type.SELF:  # accept a new connection
                    self.accept_peer(key.fileobj)
                elif key.data.type == socket_type.PEER:  # receive a message from peer
                    self.service_peer(key, mask)
                elif key.data.type == socket_type.SEED:  # receive/send a message from seed
                    self.service_seed(key, mask)

    def accept_peer(self, sock):
        """
        Accept connection from peer and add it to selector.
        Dont send peer list as we haven't received listening port yet
        """
        peer, (peer_ip, peer_port) = sock.accept()
        self.printer.print(
            f"Received connection from {peer_ip}:{peer_port}", DEBUG_MODE)
        peer.setblocking(False)
        self.sel.register(peer, read_write_mask,
                          data=Connection(peer, peer_ip, peer_port, socket_type.PEER))

    def connect_with_peers(self):

        if len(self.received_peer_list) == 0:
            self.printer.print("No other peers in the network", DEBUG_MODE)

        peer_list = getUnique(self.received_peer_list)
        self.printer.print(f"Received Peer List is {peer_list}")
        random.shuffle(peer_list)
        self.peer_list = peer_list[:min(len(peer_list), MAX_CONNECTED_PEERS)]

        for (ip, port) in self.peer_list:
            try:
                s = socket()
                s.setblocking(False)
                self.printer.print(
                    f"connecting to peer {ip}:{port}", DEBUG_MODE)
                s.connect_ex((ip, port))

                port_message = listening_port_msg.format(self.listening_port)
                s.sendall(port_message.encode(encoding))
            except:
                self.printer.print(
                    f"Failed to connect to {ip}:{port}", DEBUG_MODE)
                self.closed_sockets.append(Connection(
                    s, ip, port, sock_type=socket_type.PEER, listener_port=port))
            else:
                self.sel.register(s, read_write_mask,
                                  data=Connection(s, ip, port, sock_type=socket_type.PEER, listener_port=port))

        self.printer.print("sent connection request to all", DEBUG_MODE)
        self.printer.print(
            f"Number of out neighbours: {len(self.peer_list)}", DEBUG_MODE)
        self.start_making = True

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
        try:
            if mask & selectors.EVENT_READ:
                recv_data = sock.recv(PACKET_SIZE)
                if not recv_data:
                    self.printer.print(
                        f"closing connection to Seed {data.ip}:{data.port}", DEBUG_MODE)
                    self.sel.unregister(sock)
                    sock.close()
                else:
                    rec = json.loads(recv_data.decode(encoding))
                    self.printer.print(
                        f"Received peer list from {data.ip}:{data.port} {rec}", DEBUG_MODE)
                    self.received_peer_list += rec
                    self.received_from += 1
                    if self.received_from == len(self.seeds):
                        self.printer.print("Connecting to peers", DEBUG_MODE)
                        self.connect_with_peers()

            if mask & selectors.EVENT_WRITE:
                if not data.sent_id:  # Send listening port info
                    self.printer.print(
                        f"Sending listening info to {data.ip}:{data.port}", DEBUG_MODE)
                    port_message = listening_port_msg.format(
                        self.listening_port)
                    sock.sendall(port_message.encode(encoding))
                    data.sent_id = True
                for message in self.seed_broadcast_queue:
                    if message not in data.sent_messages:
                        self.printer.print(
                            f"Sending dead node message to {data.ip}:{data.port} {message}", DEBUG_MODE)
                        sock.sendall((message).encode(encoding))
                        data.sent_messages.append(message)
        except Exception as e:
            print(e)
            self.printer.print(
                f"closing connection to Seed {data.ip}:{data.port}", DEBUG_MODE)
            self.sel.unregister(sock)
            sock.close()

    def parse_peer_message(self, sock, data, message_combined):

        messages = message_combined.split('~')

        for message in messages:
            if message.startswith("Liveness Request"):
                if data in self.closed_sockets:
                    self.closed_sockets.remove(data)
                self.printer.print(
                    f"Received a liveness request from {data.ip}:{data.port}:{message}", DEBUG_MODE)
                # need to respond with a liveness reply
                [_, sender_date, sender_min, sender_sec,
                    sender_ip] = message.split(':')
                sender_timestamp = ':'.join(
                    [sender_date, sender_min, sender_sec])
                reply = liveness_reply_msg.format(
                    sender_timestamp, sender_ip, self.ip)
                self.printer.print(
                    f"Sending liveness reply to {data.ip}:{data.port}", DEBUG_MODE)
                sock.sendall(reply.encode(encoding))
            elif message.startswith("Liveness Reply"):
                if data in self.closed_sockets:
                    self.closed_sockets.remove(data)
                # must update that the peer is active
                self.printer.print(
                    f"Received a liveness reply from {data.ip}:{data.port} {message}", DEBUG_MODE)
                data.tries_left = MAX_TRIES
            elif message.startswith("Listening Port"):
                self.printer.print(
                    f"Received information about listening port from {data.ip}:{data.port} {message}", DEBUG_MODE)
                [_, port] = message.split(':')
                data.listener_port = int(port)
            elif message == '':
                continue
            else:
                message_hash = sha256(message.encode(encoding)).hexdigest()

                if message_hash in self.message_list.keys():
                    self.printer.print(
                        f"Received stale msg {message} from {data.ip}:{data.port}.", DEBUG_MODE)
                else:
                    self.printer.print(
                        f"Received new gossip message {message} from {data.ip}:{data.port} at {datetime.datetime.now(tz=None)}")
                    self.message_list[message_hash] = True
                    # message with sender info
                    self.peer_broadcast_queue.append(
                        (message, data.ip, data.port))

                    # self.message_list.append((hash(message), ))

    def handle_dead_peer(self, sock, data):
        current_time = datetime.datetime.now(tz=None)
        message = dead_node_msg.format(
            data.ip, data.listener_port, current_time, self.ip)
        self.seed_broadcast_queue.append(message)
        self.printer.print(
            f"Closing connection to {data.ip}:{data.port}", DEBUG_MODE)
        try:
            self.sel.unregister(sock)
            sock.close()
        except:
            pass

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
        # peer_count = 0
        # if len(self.peer_broadcast_queue) !=0):
        try:
            if mask & selectors.EVENT_READ:
                recv_data = sock.recv(PACKET_SIZE)  # Should be ready to read
                if not recv_data:
                    # print("should close connection to", data.ip, ":", data.port, "in 3 tries")
                    # Currently commented out just to check the correctness of dead node reporting
                    self.printer.print(
                        f"Closing connection to peer {data.ip}:{data.port}", DEBUG_MODE)
                    self.sel.unregister(sock)
                    self.closed_sockets.append(data)
                    sock.close()
                else:
                    self.parse_peer_message(
                        sock, data, recv_data.decode(encoding))

            if mask & selectors.EVENT_WRITE:
                # check the time since the last liveness check
                if data.liveness_timestamp is None or current_time-data.liveness_timestamp > datetime.timedelta(seconds=LIVENESS_DELAY):
                    if data.tries_left <= 0:
                        self.handle_dead_peer(sock, data)
                    else:
                        message = liveness_request_msg.format(
                            current_time, self.ip)
                        self.printer.print(
                            f"Sending liveness request to {data.ip}:{data.port}", DEBUG_MODE)
                        try:
                            sock.sendall(message.encode(encoding))
                        except:
                            self.printer.print(
                                f"failed to send liveness request to {data.ip}:{data.port}", DEBUG_MODE)
                        data.liveness_timestamp = current_time
                        data.tries_left -= 1

                for message, send_not_ip, send_not_port in self.peer_broadcast_queue:
                    message_hash = sha256(message.encode(encoding)).hexdigest()
                    if not (message_hash in data.hashed_sent):
                        if not (send_not_ip == data.ip and send_not_port == data.port):
                            time_of_msg = datetime.datetime.strptime(
                                message[:message[:message.rfind(":")].rfind(":")], '%Y-%m-%d %H:%M:%S.%f')
                            if data.created_at < time_of_msg:
                                self.printer.print(
                                    f"Sending gossip message to {data.ip}:{data.port}", DEBUG_MODE)
                                sock.sendall(message.encode(encoding))
                                data.hashed_sent.append(message_hash)
        except Exception as e:
            print(e)
            self.printer.print(
                f"Closing connection to peer {data.ip}:{data.port}", DEBUG_MODE)
            self.sel.unregister(sock)
            self.closed_sockets.append(data)
            sock.close()


if __name__ == "__main__":

    p = Peer()
    p.connect_with_seeds()
    p.run()
