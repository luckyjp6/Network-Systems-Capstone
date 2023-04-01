from setting import Setting
from protocols import aloha, slotted_aloha, csma, csma_cd
import matplotlib.pyplot as plt

# setting = Setting(host_num=3, total_time=100, packet_num=4, max_colision_wait_time=20, p_resend=0.3, packet_size=3, link_delay=1, seed=4)

# aloha_rates = aloha(setting, True)
# print(aloha_rates)
# slotted_aloha_rates = slotted_aloha(setting, True)
# print(slotted_aloha_rates)
# csma_rates = csma(setting, True)
# print(csma_rates)
# csma_cd_rates = csma_cd(setting, True)
# print(csma_cd_rates)

protocal_names = ["aloha", "slotted_aloha", "csma", "csma/cd"]

# Q1
host_num_list = [2, 3, 4, 6] #, 8, 12, 24]
packet_num_list = [1200, 800, 600, 400]#, 300, 200, 100]
rates = [[] for i in range(4)]
for h,p in zip(host_num_list, packet_num_list):
    setting = Setting(host_num=h, packet_num=p, max_colision_wait_time=20, p_resend=0.3)
    rates[0].append(aloha(setting, False))
    rates[1].append(slotted_aloha(setting, False))
    rates[2].append(csma(setting, False))
    rates[3].append(csma_cd(setting, True))
for i in range(4):
    rates[i] = [[item[j] for item in rates[i]] for j in range(len(rates[i][0]))]
# print(rates)
# sucess rate
for i in range(4):
    plt.plot(host_num_list, rates[i][0], "s-", label=protocal_names[i])
plt.plot()
plt.title("Influence of Host Num")
plt.xlabel("Host Num")
plt.ylabel("Success Rate")  
plt.legend()
plt.show()

# idle rate
for i in range(4):
    plt.plot(host_num_list, rates[i][1], "s-", label=protocal_names[i])
plt.plot()
plt.title("Influence of Host Num")
plt.xlabel("Host Num")
plt.ylabel("Idle Rate")  
plt.legend()
plt.show()

# collision rate
for i in range(4):
    plt.plot(host_num_list, rates[i][2], "s-", label=protocal_names[i])
plt.plot()
plt.title("Influence of Host Num")
plt.xlabel("Host Num")
plt.ylabel("Collision Rate")  
plt.legend(loc="best")
plt.show()