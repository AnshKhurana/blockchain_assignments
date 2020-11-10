import argparse
import os
import subprocess
import signal
import time

parser = argparse.ArgumentParser()
parser.add_argument('--nd', type=float, required=True)
parser.add_argument('--iat', type=float, required=True)
parser.add_argument('--flood_percentage', type=float, required=True)
parser.add_argument('--runtime', type=float, required=True)
parser.add_argument('--num_nodes', type=int, default=10)

args = parser.parse_args()
TIMEOUT = args.runtime * 60

def run_experiment(network_delay, interarrival_time, flood_percentage, num_nodes=10):
    # run seed
    start_time = time.time()
    log_dir =  "expt_population_nd_{}_iat_{}_fp_{}_runtime_{}".format(network_delay, interarrival_time, flood_percentage, args.runtime)
    proc_seed = subprocess.Popen("python seed.py --ip 127.0.0.1 --port 6000 --logdir {}".format(
        log_dir), shell=True, preexec_fn=os.setsid)
    time.sleep(1)
    hash_attacker = 33
    # hash_victim = flood_percentage
    # hash_honest = 100 - 33 - flood_percentage
    num_victims = int(flood_percentage*num_nodes // 100)
    hash_regular = (100-33) / (num_nodes-1)
    # run honest node
    proc_normal = dict()
    proc_victim = dict()

    for i in range(num_nodes-num_victims-1):
        proc_normal[i] = subprocess.Popen("python peer.py --draw --hash_power {}  --interarrival_time {} --net_delay {} --logdir {}".format(
            hash_regular, interarrival_time, network_delay, log_dir), shell=True, preexec_fn=os.setsid)
        # time.sleep(1) 
    # run victim node
    for i in range(num_victims):
        proc_victim[i] = subprocess.Popen("python peer.py --draw --victim --hash_power {} --interarrival_time {} --net_delay {} --logdir {}".format(
            hash_regular, interarrival_time, network_delay, log_dir), shell=True, preexec_fn=os.setsid)
        # time.sleep(1)
    # run mal node
    proc_attacker = subprocess.Popen("python peer.py  --draw --mal --hash_power {} --interarrival_time {} --net_delay {} --logdir {}".format(
        hash_attacker, interarrival_time, network_delay, log_dir), shell=True, preexec_fn=os.setsid)
    # time.sleep(1)

    # it's time to kill
    while 1:
        if (time.time() - start_time) > TIMEOUT:
            
            os.killpg(os.getpgid(proc_attacker.pid), signal.SIGINT)
            for i in proc_victim.keys():
                os.killpg(os.getpgid(proc_victim[i].pid), signal.SIGINT)
            for i in proc_normal.keys():
                os.killpg(os.getpgid(proc_normal[i].pid), signal.SIGINT)
            os.killpg(os.getpgid(proc_seed.pid), signal.SIGINT)
            # proc_victim.terminate()
            # proc_normal.terminate()
            # proc_seed.terminate()
            print("experiment terminated")
            exit()
        time.sleep(5)



if __name__ == "__main__":
    run_experiment(network_delay=args.nd, interarrival_time=args.iat, flood_percentage=args.flood_percentage, num_nodes=args.num_nodes)