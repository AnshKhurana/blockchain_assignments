## Steps to Run
```
Assignment solved by Onkar Deshpande, Kushagra Juneja, Ansh Khurana
# On seed node
$ python seed.py --ip <ip_of_seed> --port <port_of_seed>

# On peer node, config.txt must be in the same directory
$ python3 peer.py --hash_power 50 --interarrival_time 2

Here, hash_power is in percentage, interarrival_time is the global effective interarrival_time, seed denotes the random seed

# Clarifications
1. When a new peer joins the network, it syncs with all the peers connected to it and asks them for their longest chain. Then it selects the longest chain amongst those shared by the peers as its chain and mines on that. 

```
