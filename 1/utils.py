#reads the config file and returns an array of all the seeds info
def findSeeds():
    file = open('config.txt', 'r')
    seeds = file.readlines()
    seed_info = []
    for seed in seeds:
        ip = seed.split(':')[0]
        port = int(seed.split(':')[1].replace('\n',''))
        seed_info.append((ip, port))
    return seed_info

class Connection(object):
    def __init__(self, socket, ip, port):
        self.socket = socket
        self.ip = ip
        self.port = port

    # Used to share ip, port info to others
    def pretty(self):
        return (self.ip, self.port)