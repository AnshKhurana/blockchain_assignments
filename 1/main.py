# setting up the seeds first

from utils import *
import os

seeds = findSeeds()
#currently works with only one seed. change later to run each command in background to handle multiple seeds.
for (ip, port) in seeds:
    command = "python3 seed.py --ip {} --port {}".format(ip, port)
    os.system(command)