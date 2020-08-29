# code for peer when it wants to set up a TCP connection with a seed.

from socket import *
s = socket()

encoding = 'utf-8'

packet_size = 1024

port = 6000 # currently hardcoded but ideally read it from config file
ip = "127.0.0.1"

s.connect((ip, port))

message = s.recv(packet_size).decode(encoding)

print(message)

s.close()