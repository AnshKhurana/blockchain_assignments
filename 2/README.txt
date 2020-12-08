# Assumptions:

## Database for chains
The chain at each node is stored in txt files BLOCK_DB_PID.output

## Continuous Flooding:


## Network delays:
Network delay has been set to 0.5 for all the experiments. These have been introduced artificially.
@Kushagra explain why

## Verification time:
@Kushagra explain why

## Plotting runs:
IAT = [1, 2, 4, 6, 8, 10]


# Instructions for running the code:

## Running all experiments for plotting:

`python wrapper.py`

## Plotting the results of the run

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
