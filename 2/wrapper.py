import argparse
import os
import subprocess


def run_all():
    for fp in [10, 20, 30]:
        for iat in [1, 2, 4, 8, 12]:
            out = subprocess.call(
                'python run_experiments.py --nd 1 --iat {} --flood_percentage {} --runtime 12'.format(iat, fp), shell=True)


if __name__ == "__main__":
    run_all()
