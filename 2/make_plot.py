from matplotlib import pyplot as plt
from get_values import get_mpu, get_av


def save_plot(y, x, title, xtitle, ytitle, save_name):
    plt.plot(x, y)
    plt.xlabel(xtitle)
    plt.ylabel(ytitle)
    plt.title(title)
    plt.savefig('{}.png'.format(save_name))
    plt.close()


def make_plot_mpu():
    for fp in [10, 20, 30]:
        mpu = []
        avf = []
        iat_list = [1, 2, 4, 8, 12]
        for iat in iat_list:
            expt_dir = 'expt_population_nd_1.0_iat_{}.0_fp_{}.0_runtime_20.0'.format(
                iat, fp)
            print("For experiment: ", expt_dir)
            mpu.append(get_mpu(expt_dir))
            avf.append(get_av(expt_dir))
        save_plot(mpu, iat_list, 'MPU vs IAT with FP = {}'.format(
            fp), 'IAT (s)', 'MPU', 'mpu_vs_iat_fp_{}'.format(fp))
        save_plot(avf, iat_list, 'Adversary fraction vs IAT with FP = {}'.format(
            fp), 'IAT (s)', 'Fraction', 'avf_vs_iat_fp_{}'.format(fp))
        # time to make the plots


if __name__ == "__main__":
    make_plot_mpu()
