# code for seed, acts like a server

from socket import *

encoding = 'utf-8'

tcp = socket(AF_INET,SOCK_STREAM)
# listens on a socket even if previously occupied
tcp.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

port = 6000 # currently hardcoded but ideally read it from config file
ip = "127.0.0.1"
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