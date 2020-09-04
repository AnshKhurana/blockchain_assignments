"""
Usage: python seed.py --ip <ip_address> --port <port>

Seed Script. Listens for peers and maintains a peer list.
Peer list is updated using messages received from peers
"""
import json
import argparse
from socket import *
from utils import Connection, socket_type
import selectors

encoding = 'utf-8'

PACKET_SIZE = 1024

parser = argparse.ArgumentParser()
parser.add_argument('--ip', help='ip address its running on', type=str, required=True)
parser.add_argument('--port', help='port number its running on', type=int, required=True)

read_mask = selectors.EVENT_READ
read_write_mask = selectors.EVENT_READ | selectors.EVENT_WRITE

class Seed:
    def __init__(self, ip, port):
        super().__init__()
        self.ip = ip
        self.port = port
        self.peer_list = []
        self.sel = selectors.DefaultSelector()
        
    def run(self):
        # set-up listening socket for selector
        listener_socket = socket(AF_INET, SOCK_STREAM)
        # listens on a socket even if previously occupied
        listener_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        listener_socket.bind((self.ip, self.port))
        listener_socket.listen(10)
        listener_socket.setblocking(False)
        self.sel.register(listener_socket, read_mask, data=Connection(
            listener_socket, self.ip, self.port, socket_type.SELF))
        print("set up listening socket")

        while True:
            events = self.sel.select(timeout=None)
            for key, mask in events:
                if key.data.type == socket_type.SELF:  # New Peer connection
                    self.accept_peer(key.fileobj)
                elif key.data.type == socket_type.PEER: # New data received from peer
                    self.service_peer(key, mask)
        listener_socket.close()

    def parse_message(self, message):
        pass

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

    # Not sure how sendall works with select call. Definite way is to use send repeatedly

    def service_peer(self, key, mask):
        """
        Handle all messages from peer.
        Cases:
            - A peer has sent listening port. Send current peer list and add peer to peer list
            - A peer has sent dead node info. Remove peer from peer list
        """
        sock = key.fileobj
        data = key.data

        if mask & selectors.EVENT_READ:
            try:
                recv_data = sock.recv(PACKET_SIZE).decode(encoding)
                print(recv_data)
                if not recv_data:
                    print("closing connection to", data.ip, ":", data.port)
                    self.sel.unregister(sock)
                    sock.close()
                
                # peer has sent listening port
                elif data.listener_port is None:
                    id = json.loads(recv_data)
                    print("received listening port info", id)
                    pretty_peers = [connection.pretty()
                                    for connection in self.peer_list]
                    sock.sendall(json.dumps(pretty_peers).encode(encoding))
                    key.data.listener_port = id['port']
                    self.peer_list.append(key.data)
                
                else:  # dead node info
                    print("received from", data.ip, ":", data.port, ":", recv_data)
                    parse_message(recv_data)
            
            except Exception as e:
                print(e)
                self.sel.unregister(sock)
                sock.close()

        if mask & selectors.EVENT_WRITE:
            pass
        
if __name__ == "__main__":
    args = parser.parse_args()
    s = Seed(args.ip, args.port)
    s.run()