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
import argparse

encoding = 'utf-8'

# GLOBAL VARIABLES
PACKET_SIZE = 1024
MAX_CONNECTED_PEERS = 4
LIVENESS_DELAY = 13  # 13 seconds for each message

parser = argparse.ArgumentParser()
parser.add_argument('--interarrival_time', type=float, required=True,
                    help="Set interrarival time for generation of blocks")
parser.add_argument('--hash_power', type=float, required=True,
                    help="Set hashing power of this node")
# parser.add_argument('--seed', type=int, required=True)
parser.add_argument('--net_delay', type=float, required=True,
                    help="Set network delay faced by this node in the P2P network")
parser.add_argument('--draw', action='store_true',
                    help="Set to draw the blockchain tree")
parser.add_argument('--logdir', type=str,
                    help='path to save all experiment related files', default='./log')
parser.add_argument('--mal', action='store_true',
                    help="Set to make this node an attacker")
parser.add_argument('--victim', action='store_true',
                    help="Set to make this node a victim of flooding")


class Peer:
    def __init__(self, args):
        super().__init__()

        self.is_mal = args.mal
        self.is_victim = args.victim
        self.info_file = os.path.join(args.logdir, 'victim_nodes.output')
        if self.is_victim and self.is_mal:
            raise ValueError(
                "Cannot be both attacker and victim at the same time")

        seeds = findSeeds()
        N = len(seeds)
        # select n//2+1 seeds randomly
        random.shuffle(seeds)
        self.seeds = seeds[:N//2+1]

        self.received_peer_list = []
        self.received_from = 0
        self.peer_list = []
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

        self.message_list = dict()
        self.peer_broadcast_queue = []

        self.printer = Printer('PEER', args.logdir, self.is_mal)
        self.printer.print(
            f"Listening on port {self.listening_port}", DEBUG_MODE)

        self.miner = Miner(interarrival_time=args.interarrival_time,
                           percentage_hash_power=args.hash_power,
                           draw=args.draw,
                           logfolder=args.logdir,
                           is_mal=self.is_mal)

        self.mine_timestamp = None
        self.start_mining = False
        self.synced_with = 0  # Number of peers I have synced the blockchain with
        self.mine_delay = None
        self.peer_list_valid = False

        self.net_delay_mean = args.net_delay
        self.delayed_timestamp = datetime.datetime.now(tz=None)

        # if you're a victim, write information for the attacker
        if self.is_victim:
            with open(self.info_file, 'a+') as file:
                file.write(
                    ":".join(["127.0.0.1", str(self.listening_port)]) + '\n')

        # if you're an attacker, mark nodes to flood
        if self.is_mal:
            try:
                with open(self.info_file, 'r') as file:
                    peers = file.readlines()
                    peer_info = []
                    for peer in peers:
                        ip = peer.split(':')[0]
                        port = int(peer.split(':')[1].replace('\n', ''))
                        peer_info.append((ip, port))
                    self.peers_to_flood = peer_info
            except:
                self.peers_to_flood = []
                self.printer.print(f"No peers to flood.", DEBUG_MODE)
        else:
            self.peers_to_flood = []

        self.printer.print(
            f"peers_to_flood are {self.peers_to_flood}", DEBUG_MODE)

        self.prev_msg = ''  # This is needed if while receiving, some msg comes only halfway

        self.processing_resume = datetime.datetime.now(tz=None)

    def get_delayed_timestamp(self):
        return datetime.timedelta(seconds=self.net_delay_mean) + datetime.datetime.now(tz=None)

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

            current_time = datetime.datetime.now(tz=None)
            # It has synced blockchain with all peers, now it can start mining
            if self.peer_list_valid and self.synced_with == len(self.peer_list) and not self.start_mining:
                self.start_mining = True
                self.mine_timestamp = current_time
                self.mine_delay = self.miner.waiting_time()

            # Delay added in validation of blocks is complete
            if datetime.datetime.now(tz=None) >= self.processing_resume:
                # Non-empty pending queue -> stop mining, process the pending_queue and broadcast valid blocks
                if not self.miner.pending_queue.empty():
                    block_strings, delay = self.miner.process_pending_queue()
                    self.processing_resume = current_time + delay
                    for block_string, send_not_ip, send_not_port in block_strings:
                        self.peer_broadcast_queue.append(
                            (block_msg.format(block_string), send_not_ip, send_not_port))
                        message_hash = sha256(
                            block_string.encode(encoding)).hexdigest()
                        self.message_list[message_hash] = True
                    current_time = datetime.datetime.now(tz=None)
                    self.mine_timestamp = self.processing_resume
                    self.mine_delay = self.miner.waiting_time()

            if datetime.datetime.now(tz=None) >= self.processing_resume:
                # Block generation and broadcasting
                if self.start_mining and (current_time - self.mine_timestamp) > self.mine_delay:
                    block_string, block_hash = self.miner.mine()
                    self.printer.print(
                        f"Generated a block: {block_string} with hash {block_hash}", DEBUG_MODE)
                    self.peer_broadcast_queue.append(
                        (block_msg.format(block_string), None, None))
                    message_hash = sha256(
                        block_string.encode(encoding)).hexdigest()
                    self.message_list[message_hash] = True
                    self.mine_timestamp = current_time
                    self.mine_delay = self.miner.waiting_time()

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
        data = Connection(peer, peer_ip, peer_port,
                          socket_type.PEER)
        data.sent_k = False
        for message, _, _ in self.peer_broadcast_queue:
            message_hash = sha256(message.encode(encoding)).hexdigest()
            data.hashed_sent.append(message_hash)
        self.sel.register(peer, read_write_mask,
                          data=data)

    def connect_with_peers(self):

        if len(self.received_peer_list) == 0:
            self.printer.print("No other peers in the network", DEBUG_MODE)

        peer_list = getUnique(self.received_peer_list)
        self.printer.print(f"Received Peer List is {peer_list}")
        random.shuffle(peer_list)
        self.peer_list = peer_list[:min(len(peer_list), MAX_CONNECTED_PEERS)]
        self.peer_list_valid = True
        self.peer_list.extend(self.peers_to_flood)
        self.peer_list = getUnique(self.peer_list)

        for (ip, port) in self.peer_list:
            try:
                s = socket()
                s.setblocking(False)
                self.printer.print(
                    f"connecting to peer {ip}:{port}", DEBUG_MODE)
                s.connect_ex((ip, port))
            except Exception as e:
                self.printer.print(f"Error: {e}", DEBUG_MODE)
                self.printer.print(
                    f"Failed to connect to {ip}:{port}", DEBUG_MODE)
            else:
                self.printer.print(
                    f"checking {ip}:{port} in {self.peers_to_flood}", DEBUG_MODE)
                if (ip, port) in self.peers_to_flood:
                    data = Connection(s, ip, port, sock_type=socket_type.PEER,
                                      listener_port=port, to_flood=True)
                else:
                    data = Connection(s, ip, port, sock_type=socket_type.PEER,
                                      listener_port=port)
                self.sel.register(s, read_write_mask,
                                  data=data)

        self.printer.print("sent connection request to all", DEBUG_MODE)
        self.printer.print(
            f"Number of out neighbours: {len(self.peer_list)}", DEBUG_MODE)

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
                            f"Reporting dead node message to {data.ip}:{data.port} {message}", DEBUG_MODE)
                        sock.sendall((message).encode(encoding))
                        data.sent_messages.append(message)
        except Exception as e:
            print(str(e))
            self.printer.print(
                f"closing connection to Seed {data.ip}:{data.port}", DEBUG_MODE)
            self.sel.unregister(sock)
            sock.close()

    def parse_peer_message(self, sock, data, message_combined):

        messages = message_combined.split('~')

        # This part helps to deal with messages that get cut in half due to socket limits
        # this now happens with high probabilty due to flooding
        messages[0] = self.prev_msg+messages[0]
        self.prev_msg = messages[-1]

        for message in messages[:-1]:
            if message.startswith("Liveness Request"):
                self.printer.print(
                    f"Received a liveness request from {data.ip}:{data.port}:{message}", LIVENESS_DEBUG_MODE)
                # need to respond with a liveness reply
                [_, sender_date, sender_min, sender_sec,
                    sender_ip, sender_port] = message.split(':')
                sender_timestamp = ':'.join(
                    [sender_date, sender_min, sender_sec])
                reply = liveness_reply_msg.format(
                    sender_timestamp, sender_ip, sender_port, self.ip, self.listening_port)
                self.printer.print(
                    f"Sending liveness reply to {data.ip}:{data.listener_port}", LIVENESS_DEBUG_MODE)
                sock.sendall(reply.encode(encoding))
            elif message.startswith("Liveness Reply"):
                # must update that the peer is active
                self.printer.print(
                    f"Received a liveness reply from {data.ip}:{data.port} {message}", LIVENESS_DEBUG_MODE)
                data.tries_left = MAX_TRIES
            elif message.startswith("Listening Port"):
                self.printer.print(
                    f"Received information about listening port from {data.ip}:{data.port} {message}", DEBUG_MODE)
                [_, port] = message.split(':')
                data.listener_port = int(port)
            elif message.startswith("Height"):
                [_, k] = message.split(':')
                self.printer.print(
                    f"Received k = {k} from {data.ip}:{data.port} via: {message}", DEBUG_MODE)
                data.k = int(k)
            elif message.startswith("Sync Complete"):
                self.printer.print(
                    f"Received {message} from {data.ip}:{data.port} via: {message}", DEBUG_MODE)
                self.synced_with += 1
            elif message == '':
                continue
            else:
                try:
                    message_hash = sha256(message.encode(encoding)).hexdigest()

                    if message_hash in self.message_list.keys():
                        self.printer.print(
                            f"Received stale block {message} from {data.ip}:{data.port}.", DEBUG_MODE)
                    else:
                        self.message_list[message_hash] = True
                        block = Block(message)
                        self.printer.print(
                            f"Received new block: {message} with hash {block.sha3()} from {data.ip}:{data.port} at {datetime.datetime.now(tz=None)}", DEBUG_MODE)
                        if block.level >= data.k:
                            self.miner.add_to_pending_queue(
                                block, data.ip, data.port)
                        else:
                            if self.mine_delay is not None:
                                self.mine_delay += validation_delay
                            self.miner.add_to_tree(block)
                except:
                    pass

    def handle_dead_peer(self, sock, data):
        current_time = datetime.datetime.now(tz=None)
        message = dead_node_msg.format(
            data.ip, data.listener_port, current_time, self.ip)
        self.seed_broadcast_queue.append(message)
        self.printer.print(f"Reporting {message}")
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
            - Handle block and liveness messages
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
                    pass
                    # print("should close connection to", data.ip, ":", data.port, "in 3 tries")
                    # Currently commented out just to check the correctness of dead node reporting
                    # self.printer.print(
                    #     f"Closing connection to peer {data.ip}:{data.port}", DEBUG_MODE)
                    # self.sel.unregister(sock)
                    # sock.close()
                    # if data.listener_port:
                    #     self.handle_dead_peer(sock, data)
                else:
                    self.parse_peer_message(
                        sock, data, recv_data.decode(encoding))

            if mask & selectors.EVENT_WRITE:
                # check the time since the last liveness check
                if not data.sent_id:  # Send listening port info
                    self.printer.print(
                        f"Sending listening info to {data.ip}:{data.port}", DEBUG_MODE)
                    port_message = listening_port_msg.format(
                        self.listening_port)
                    try:
                        sock.sendall(port_message.encode(encoding))
                    except:
                        pass
                    data.sent_id = True

                # send height info and then send all the blocks
                elif not data.sent_k:
                    height_message = height_msg.format(
                        self.miner.blockchain.max_level)
                    self.printer.print(
                        f"Sending message {height_message} to {data.ip}:{data.port}", DEBUG_MODE)
                    try:
                        sock.sendall(height_message.encode(encoding))
                    except:
                        pass
                    data.sent_k = True

                    # Syncing my blocks
                    block_strings = self.miner.get_blocks_in_chain()
                    for block_string in block_strings:
                        block_message = block_msg.format(block_string)
                        self.printer.print(
                            f"Syncing my block: {block_string} with {data.ip}:{data.port}", DEBUG_MODE)
                        try:
                            sock.sendall(block_message.encode(encoding))
                        except:
                            pass

                    # Send sync complete message to peer
                    self.printer.print(
                        f"Sending {sync_complete_msg} to {data.ip}:{data.port}", DEBUG_MODE)
                    try:
                        sock.sendall(sync_complete_msg.encode(encoding))
                    except:
                        pass

                elif data.liveness_timestamp is None or current_time-data.liveness_timestamp > datetime.timedelta(seconds=LIVENESS_DELAY):

                    if data.tries_left <= 0:
                        self.handle_dead_peer(sock, data)
                    else:
                        message = liveness_request_msg.format(
                            current_time, self.ip, self.listening_port)
                        self.printer.print(
                            f"Sending liveness request to {data.ip}:{data.port}", LIVENESS_DEBUG_MODE)
                        try:
                            sock.sendall(message.encode(encoding))
                        except:
                            pass
                            # self.printer.print(
                            #     f"failed to send liveness request to {data.ip}:{data.port}", LIVENESS_DEBUG_MODE)
                        data.liveness_timestamp = current_time
                        data.tries_left -= 1

                elif len(data.delayed_queue) > 0 and datetime.datetime.now(tz=None) > data.delayed_queue[0][1]:
                    try:
                        sock.sendall(data.delayed_queue[0][0])
                    except:
                        pass
                    data.delayed_queue.pop(0)
                    # print(data.delayed_queue)

                else:
                    for message, send_not_ip, send_not_port in self.peer_broadcast_queue:
                        message_hash = sha256(
                            message.encode(encoding)).hexdigest()
                        if not (message_hash in data.hashed_sent):
                            if not (send_not_ip == data.ip and send_not_port == data.port):
                                self.printer.print(
                                    f"Sending block: {message} to {data.ip}:{data.port}", DEBUG_MODE)
                                data.delayed_queue.append(
                                    (message.encode(encoding), self.get_delayed_timestamp()))
                                data.hashed_sent.append(message_hash)

                    # Flood with bad block
                    if data.to_flood and datetime.datetime.now(tz=None) - data.last_flooded >= datetime.timedelta(milliseconds=1):
                        data.last_flooded = datetime.datetime.now(tz=None)
                        block_string, block_hash = self.miner.mine(
                            malicious=True)
                        self.printer.print(
                            f"Flooding block: {block_string} with hash {block_hash} to {data.ip}:{data.port}", PRINT_FLOODS)
                        # We don't want to fill our own RAM while flooding
                        if len(data.delayed_queue) < 1e6:
                            data.delayed_queue.append((block_msg.format(
                                block_string).encode(encoding), self.get_delayed_timestamp()))

        except Exception as e:
            print(str(e))
            self.printer.print(
                f"Closing connection to peer {data.ip}:{data.port}", DEBUG_MODE)
            self.sel.unregister(sock)
            sock.close()
            if data.listener_port:
                self.handle_dead_peer(sock, data)


if __name__ == "__main__":
    args = parser.parse_args()

    # create log dir
    check_and_make_dir(args.logdir)

    p = Peer(args)
    p.connect_with_seeds()
    p.run()
