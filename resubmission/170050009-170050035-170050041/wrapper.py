import argparse
import os
import subprocess


def run_all():
    for fp in [10]:
        for iat in [1, 2, 4, 6, 8, 10]:
            out = subprocess.call(
                'python3 run_experiments.py --nd 0.5 --iat {} --flood_percentage {} --runtime 10'.format(iat, fp), shell=True)


if __name__ == "__main__":
    run_all()
