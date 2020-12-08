# Assumptions and implementation details:

## Role of nodes:
Seed nodes are not considered regular nodes in the P2P network and do not participate in any protocols other than connecting new peers to the network.

## Syncing 
When a new peer joins a network, it syncs with all the max 4 peers it is connected to i.e. asks all of them to give the longest chain available to each of them and from all the received blocks, constructs the overall longest chain available in the network. When a peer generates a block, it also send the height of the  block in the chain, which determines whether it is to be put in the pending queue or directly on the chain post validation by the receiving peer.

## Picking which chain to mine on when encountering forks:
We assume that the longest chain is the main chain. Further, if there are two forks of the same length, we mine on the one we received earlier.

## Contents of the blockchain block
These are the contents of any block: self.previous_hash, self.merkel_root, self.timestamp, self.level
level = level in the blockchain tree
timestamp = generation timestamp
merkel_root = deterministically set to "0000"
previous_hash = hash of the previous block in the chain

## Database for chains:
The blockchain tree at each node is stored in txt files BLOCK_DB_PID.output. This database is then used to generate the plots.

## Continuous Flooding:
Our malicious node floods the victim nodes continuously each after an interval of 1ms and essentially blocks the victim nodes by flooding their verification queue.

## Verification time:
We have simulated verification time of a block to be 2ms i.e. for each received block, a peer is expected to spend 2ms in verifying if the received block is valid in the blockchain or not.

## Using socket select calls
We do not use multi-threading in our code. All processes are handling by socket selection. 

## Assigning which nodes to flood
Since we need to ensure that all victim nodes' hashing power has to sum up to flooding percentage and the malicious node has no way of estimating the hash power of each node, the nodes which have to be flooded are predecided by giving the --victim flag and the malicious nodes chooses to flood these.

## Flooding x% of Nodes:
In the problem statement it was written that 10,20,30 % of the nodes have to be flooded. This has been assumed to be referring percentage in terms of 10,20,30% of the hashing power of the entire network. Thus, we make the malicious node flood nodes such that the total hash power of the nodes that are being flooded sum up to the hashing power. 

In one experiment, we have given the entire flood percentage of hashing power to one node, 33% of hashing power to the malicious node, and rest of the hasing power is given to another node. So a total of 3 peer nodes make this simulation.

In experiment 2, we keep 10 nodes, and divide the fp = [10,20,30] hash power among 10,20,30% population of the nodes.

## Network delays:
Network delay has been set to 0.5 for all the experiments. These have been simulated by mantaining a delay queue for each connection. As soon as a message is intended to be sent to a peer, its first sent to this queue along with a timestamp=current_time+delay indicating that this message is to be sent only when the current time is >= timestamp. The delay queue is checked frequently, and once the timer of a message expires, it is sent to the other peer and the other peer receives the message instantly, but the total delay = 0.5 due to late sending of the message.

## Plotting runs:
IAT = [1, 2, 4, 6, 8, 10]

# Instructions for running the code:

## Running experiment 1 for data generation (3 peers):

`python wrapper.py`

## Running experiment 2 for data generation (10 peers):

`python population_wrapper.py`

## Plotting the results of the run - adjust per experiment

`python make_plot.py`

## Individual seed and peer nodes can be launched using the following commands:

```
python seed.py [-h] --ip IP --port PORT [--logdir LOGDIR]

optional arguments:
  -h, --help       show this help message and exit
  --ip IP          ip address its running on
  --port PORT      port number its running on
  --logdir LOGDIR  path to save all experiment related files
```

```
python peer.py [-h] --interarrival_time INTERARRIVAL_TIME --hash_power
               HASH_POWER --net_delay NET_DELAY [--draw] [--logdir LOGDIR]
               [--mal] [--victim]

optional arguments:
  -h, --help            show this help message and exit
  --interarrival_time INTERARRIVAL_TIME
                        Set interrarival time for generation of blocks
  --hash_power HASH_POWER
                        Set hashing power of this node
  --net_delay NET_DELAY
                        Set network delay faced by this node in the P2P
                        network
  --draw                Set to draw the blockchain tree
  --logdir LOGDIR       path to save all experiment related files
  --mal                 Set to make this node an attacker
  --victim              Set to make this node a victim of flooding
```

# References:
1. http://www.dabeaz.com/python/PythonNetBinder.pdf
2. https://realpython.com/python-sockets/
3. Lecture Notes
