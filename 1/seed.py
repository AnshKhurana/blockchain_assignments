"""
Usage: python seed.py --ip <ip_address> --port <port>

Seed Script. Listens for peers and maintains a peer list.
Peer list is updated using messages received from peers
"""
import json
import argparse
from socket import *
from utils import Connection
import selectors
sel = selectors.DefaultSelector()

encoding = 'utf-8'

parser = argparse.ArgumentParser()
parser.add_argument('--ip', help='ip address its running on', required=True)
parser.add_argument('--port', help='port number its running on', required=True)

args = parser.parse_args()

port = int(args.port)
ip = str(args.ip)  # should be empty while submitting

peer_list = []


def handle_delete(message):
    print(message)


def accept_peer(sock):
    peer, (peer_ip, peer_port) = sock.accept()
    print("Received connection from", peer_ip, peer_port)
    peer.setblocking(False)

    # Might need to ensure you dont send a peer to itself
    pretty_peers = [connection.pretty() for connection in peer_list]
    # send() can send partial data too, use sendall() to avoid confusion and blocks till all data is sent
    # convert str into bytes before sending.
    # Not sure how sendall works with select call. Definite way is to use send repeatedly
    peer.sendall(json.dumps(pretty_peers).encode(encoding))
    print("Sent peer list")

    conn = Connection(peer, peer_ip, peer_port)
    sel.register(peer, selectors.EVENT_READ | selectors.EVENT_WRITE, data=conn)
    peer_list.append(conn)


def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        try:  # Find a better place for this
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                handle_delete(recv_data.decode(encoding))
        except Exception as e:
            print(e)

    # if mask & selectors.EVENT_WRITE:
    #     pass


server_socket = socket(AF_INET, SOCK_STREAM)
# listens on a socket even if previously occupied
server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
server_socket.bind((ip, port))
server_socket.listen(10)
server_socket.setblocking(False)
sel.register(server_socket, selectors.EVENT_READ, data=None)


while True:
    events = sel.select(timeout=None)
    # print("found events")
    for key, mask in events:
        # print("found key", mask)
        if key.data is None:  # New Peer connection
            accept_peer(key.fileobj)
        else:
            service_connection(key, mask)


server_socket.close()
