import os
import glob
import argparse
import pandas

parser = argparse.ArgumentParser()

parser.add_argument('--experiment_root_dir', type=str, required=True)

def get_mpu(root_path_dir):
    file_list = glob.glob(os.path.join(root_path_dir, '*BLOCK_DB*.output'))
    mpu = 0
    for file in file_list:
        block_db = pandas.read_csv(file, sep = '_', header = None)
        longest_chain = block_db[4].max()
        total_blocks = len(block_db)
        mpu_f = longest_chain/total_blocks 
        print(longest_chain, total_blocks)
        print("file: ", file, mpu_f)
        mpu+=mpu_f
    
    return mpu / len(file_list)

def get_av(root_path_dir):
    av = 0
    file_list = glob.glob(os.path.join(root_path_dir, 'MAL_BLOCK_DB*.output'))
    if len(file_list) !=1:
        raise ValueError("unexpected")
    file = file_list[0]
    block_db = pandas.read_csv(file, sep = '_', header = None)
    longest_chain = block_db[4].max()
    long_ch_id = block_db[4].idxmax()

    num_mine = 0
    while (block_db.iloc[long_ch_id, 1] != '9e1c'):
        # print(long_ch_id)
        if block_db.iloc[long_ch_id, 5] == 'generated':
            num_mine+=1
        prev = block_db.iloc[long_ch_id, 1]
        long_ch_id = block_db[block_db[0]==prev].index[0]
        
        
    if block_db.iloc[long_ch_id, 5] == 'generated':
        num_mine+=1

    print(num_mine, longest_chain)
    av = num_mine / longest_chain
    print("file: ", file, av)
    return av
    

if __name__ == "__main__":
    args=parser.parse_args()
    print("Mining Power Utilization")
    get_mpu(args.experiment_root_dir)
    print("Fraction of Blocks from Adversary in the main blockchain")
    get_av(args.experiment_root_dir)