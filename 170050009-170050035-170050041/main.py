"""
Usage: python main.py
TODO add custom config path

Seed Generator Script. Generates seed nodes
"""

from utils import *
import subprocess
import time
import signal

seeds = findSeeds()
NUM_PEERS = 5
seed_procs = []
peer_procs = []
# currently works with only one seed. change later to run each command in background to handle multiple seeds.
for (ip, port) in seeds:
    proc = subprocess.Popen(
        ['python', 'seed.py', '--ip', str(ip), '--port', str(port)])
    seed_procs.append(proc)

time.sleep(1)

for _ in range(NUM_PEERS):
    proc = subprocess.Popen(
        ['python', 'peer.py'])
    peer_procs.append(proc)


def killall(signal_number, frame):
    print("Caught")
    for proc in seed_procs:
        try:
            proc.terminate()
        except:
            pass

    for proc in peer_procs:
        try:
            proc.terminate()
        except:
            pass
    exit(0)


signal.signal(signal.SIGKILL, killall)

while True:
    pass
