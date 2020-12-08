from matplotlib import pyplot as plt
from get_values import get_mpu, get_av


def save_plot_combined(values, x_list, title, xtitle, ytitle, save_name):
    for fp in values.keys():
        print(fp, values[fp])
        plt.plot(x_list, values[fp], label='fp={}'.format(fp), marker='^')

    # plt.xscale("log")
    plt.legend()
    plt.xticks(x_list, x_list)
    plt.title(title)
    plt.xlabel(xtitle)
    plt.ylabel(ytitle)
    plt.savefig(save_name)
    plt.close()

def save_plot(y, x, title, xtitle, ytitle, save_name):
    plt.plot(x, y)
    plt.xlabel(xtitle)
    plt.ylabel(ytitle)
    plt.title(title)
    plt.savefig('{}.png'.format(save_name))
    plt.close()


def make_plot_combined():
    mpu = dict()
    avf = dict()
    iat_list = [1, 2, 4, 6, 8, 10]
    for fp in [10, 20, 30]:
        mpu_v = []
        avf_v = []
        for iat in iat_list:
            expt_dir = 'expt_nd_0.5_iat_{}.0_fp_{}.0_runtime_10.0'.format(iat, fp)
            print("For experiment: ", expt_dir)
            mpu_v.append(get_mpu(expt_dir))
            avf_v.append(get_av(expt_dir))
        mpu[fp] = mpu_v
        avf[fp] = avf_v

    save_plot_combined(mpu, iat_list, "MPU vs IAT", 'IAT (s)', 'MPU', 'mpu_vs_iat')
    save_plot_combined(avf, iat_list, "Adversary fraction vs IAT", 'IAT (s)', 'Ad', 'avf_vs_iat')

def make_plot_single():
    for fp in [10]:
        mpu = []
        avf = []
        iat_list = [1, 2, 4, 6, 8, 10]
        for iat in iat_list:
            expt_dir = 'expt_nd_0.5_iat_{}.0_fp_{}.0_runtime_10.0'.format(
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
    make_plot()
