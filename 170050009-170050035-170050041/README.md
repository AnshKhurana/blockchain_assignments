## Steps to Run
```
Assignment solved by Onkar Deshpande, Kushagra Juneja, Ansh Khurana
# On seed node
$ python seed.py --ip <ip_of_seed> --port <port_of_seed>

# On peer node, config.txt must be in the same directory
$ python peer.py

Gossip messages are numbered starting from 0.
malicious_peer.py does not reply to liveness requests hence other peers hence others must close connection to it after 3 tries.
```
