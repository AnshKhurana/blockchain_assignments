# code for seed, acts like a server

import argparse
from socket import *

encoding = 'utf-8'

parser = argparse.ArgumentParser()
parser.add_argument('--ip',help='ip address its running on', required=True)
parser.add_argument('--port', help='port number its running on', required=True)

args = parser.parse_args()

port = int(args.port)
ip = str(args.ip)

tcp = socket(AF_INET,SOCK_STREAM)
# listens on a socket even if previously occupied
tcp.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

tcp.bind((ip,port))

tcp.listen(10)

while True:
    #blocks till new connection is achieved
    client,(client_ip, client_port) = tcp.accept()
    print("Received connection from", client_ip)
    #server socket is only used for new connections, send/receive on client socket
    # send() can send partial data too, use sendall() to avoid confusion and blocks till all data is sent
    # convert str into bytes before sending.
    client.sendall("Hello".encode(encoding))
    client.close()