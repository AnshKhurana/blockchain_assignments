import argparse
import os
import subprocess

parser = argparse.ArgumentParser()

runtime = 20
nd = 0.5

def run_all(runtime, nd):
    for fp in [20]:
        for iat in [1, 2, 4]:
            out = subprocess.call(
                'python3 run_more_nodes.py --nd {} --iat {} --flood_percentage {} --runtime {}'.format(nd, iat, fp, runtime), shell=True)


if __name__ == "__main__":
    args=parser.parse_args()
    run_all(runtime, nd)
