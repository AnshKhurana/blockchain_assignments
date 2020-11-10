import argparse
import os
import subprocess

parser = argparse.ArgumentParser()

parser.add_argument('--runtime', type=float, default=12)
parser.add_argument('--nd', type=int, default=1)

def run_all(runtime, nd):
    for fp in [10, 20, 30]:
        for iat in [1, 2, 4, 8, 12]:
            out = subprocess.call(
                'python run_more_nodes.py --nd {} --iat {} --flood_percentage {} --runtime {}'.format(nd, iat, fp, runtime), shell=True)


if __name__ == "__main__":
    args=parser.parse_args()
    run_all(args.runtime, args.nd)
