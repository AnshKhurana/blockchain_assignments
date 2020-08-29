# code for peer when it wants to set up a TCP connection with a seed.

from socket import *
from utils import *

encoding = 'utf-8'

# receive in blocks of packet_size
packet_size = 1024

seeds = findSeeds()

s = socket()
s.connect((ip, port))

message = s.recv(packet_size).decode(encoding)

print(message)

s.close()