import argparse
import os
import subprocess

parser = argparse.ArgumentParser()

runtime = 20
nd = 0.5

def run_all(runtime, nd):
    for fp in [10, 20, 30]:
        for iat in [1, 2, 4, 6, 8, 10]:
            out = subprocess.call(
                'python3 run_more_nodes.py --nd {} --iat {} --flood_percentage {} --runtime {}'.format(nd, iat, fp, runtime), shell=True)


if __name__ == "__main__":
    args=parser.parse_args()
    run_all(args.runtime, args.nd)
