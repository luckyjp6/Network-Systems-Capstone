from setting import Setting
from protocols import aloha, slotted_aloha, csma, csma_cd
import matplotlib.pyplot as plt

def test():
    setting = Setting(host_num=3, total_time=100, packet_num=4, max_colision_wait_time=20, p_resend=0.3, packet_size=3, link_delay=1, seed=4)

    aloha_rates = aloha(setting, True)
    print(aloha_rates)
    slotted_aloha_rates = slotted_aloha(setting, True)
    print(slotted_aloha_rates)
    csma_rates = csma(setting, True)
    print(csma_rates)
    csma_cd_rates = csma_cd(setting, True)
    print(csma_cd_rates)

protocal_names = ["aloha", "slotted_aloha", "csma", "csma/cd"]
host_num_list = [2, 3, 4, 6]
packet_num_list = [1200, 800, 600, 400]
rates = [[] for i in range(4)]
def plot(title, x_label, target):
    global protocal_names, rates
    num_proc = len(rates)
    # sucess rate
    for i in range(num_proc):
        plt.plot(target, rates[i][0], "s-", label=protocal_names[i])
    plt.plot()
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel("Success Rate")  
    plt.legend()
    plt.show()

    # idle rate
    for i in range(num_proc):
        plt.plot(target, rates[i][1], "s-", label=protocal_names[i])
    plt.plot()
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel("Idle Rate")  
    plt.legend()
    plt.show()

    # collision rate
    for i in range(num_proc):
        plt.plot(target, rates[i][2], "s-", label=protocal_names[i])
    plt.plot()
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel("Collision Rate")  
    plt.legend(loc="best")
    plt.show()

def Q1():
    global rates, host_num_list, packet_num_list
    for h,p in zip(host_num_list, packet_num_list):
        setting = Setting(host_num=h, packet_num=p, max_colision_wait_time=20, p_resend=0.3)
        rates[0].append(aloha(setting, False))
        rates[1].append(slotted_aloha(setting, False))
        rates[2].append(csma(setting, False))
        rates[3].append(csma_cd(setting, False))
    for i in range(4):
        rates[i] = [[item[j] for item in rates[i]] for j in range(len(rates[i][0]))]
    plot("Influence of Host Num", "Host Num", host_num_list)

def Q3():
    global rates, host_num_list, packet_num_list
    for h,p in zip(host_num_list, packet_num_list):
        setting = Setting(host_num=h, packet_num=p, coefficient=1)
        rates[0].append(aloha(setting, False))
        rates[1].append(slotted_aloha(setting, False))
        rates[2].append(csma(setting, False))
        rates[3].append(csma_cd(setting, False))
    for i in range(4):
        rates[i] = [[item[j] for item in rates[i]] for j in range(len(rates[i][0]))]
    plot("Influence of Host Num", "Host Num", host_num_list)

def Q4():
    global rates
    total_simulation = 100
    c_max = 31
    rates = [[[] for j in range(1, c_max)] for i in range(4)]
    for i in range(total_simulation):
        for c in range(1, c_max):
            setting = Setting(coefficient=c)
            rates[0][c-1].append(aloha(setting, False))
            rates[1][c-1].append(slotted_aloha(setting, False))
            rates[2][c-1].append(csma(setting, False))
            rates[3][c-1].append(csma_cd(setting, False))
    for i in range(4):
        for c in range(1, c_max):
            t = rates[i][c-1]
            t = [[t[m][n] for m in range(total_simulation)] for n in range(3)]
            rates[i][c-1] = [sum(x)/total_simulation for x in t]
    rates = [[[rates[p][i][j] for i in range(len(rates[p]))] for j in range(len(rates[p][0]))] for p in range(4)]
    
    plot("Influence of Coefficient", "Coefficient", [c for c in range(1, c_max)])

def Q5():
    global rates
    total_simulation = 100
    rates = [[] for i in range(4)]
    for p in range(100, 1050, 50):
        t = [[] for i in range(4)]
        setting = Setting(packet_num=p)
        for i in range(total_simulation):
            t[0].append(aloha(setting, False))
            t[1].append(slotted_aloha(setting, False))
            t[2].append(csma(setting, False))
            t[3].append(csma_cd(setting, False))
        
        t = [[[t[pro][m][n] for m in range(total_simulation)] for n in range(3)] for pro in range(4)]
        t = [[sum(x)/total_simulation for x in t[pro]] for pro in range(4)]
        for i in range(4): rates[i].append(t[i])
    rates = [[[rates[i][p][r] for p in range(len(rates[i]))] for r in range(3)] for i in range(4)]
    plot("Influence of Packet Num", "Packet Num", [p for p in range(100, 1050, 50)])

def Q6(): 
    global rates
    total_simulation = 100
    rates = [[] for i in range(4)]
    for h in range(1, 11):
        t = [[] for i in range(4)]
        setting = Setting(host_num=h)
        for i in range(total_simulation):
            t[0].append(aloha(setting, False))
            t[1].append(slotted_aloha(setting, False))
            t[2].append(csma(setting, False))
            t[3].append(csma_cd(setting, False))
        
        t = [[[t[pro][m][n] for m in range(total_simulation)] for n in range(3)] for pro in range(4)]
        t = [[sum(x)/total_simulation for x in t[pro]] for pro in range(4)]
        for i in range(4): rates[i].append(t[i])
    rates = [[[rates[i][p][r] for p in range(len(rates[i]))] for r in range(3)] for i in range(4)]
    plot("Influence of Host Num", "Host Num", [p for p in range(1, 11)])

def Q7(): 
    global rates
    total_simulation = 100
    rates = [[] for i in range(4)]
    for p in range(1, 20):
        t = [[] for i in range(4)]
        setting = Setting(packet_size=p)
        for i in range(total_simulation):
            t[0].append(aloha(setting, False))
            t[1].append(slotted_aloha(setting, False))
            t[2].append(csma(setting, False))
            t[3].append(csma_cd(setting, False))
        
        t = [[[t[pro][m][n] for m in range(total_simulation)] for n in range(3)] for pro in range(4)]
        t = [[sum(x)/total_simulation for x in t[pro]] for pro in range(4)]
        for i in range(4): rates[i].append(t[i])
    rates = [[[rates[i][p][r] for p in range(len(rates[i]))] for r in range(3)] for i in range(4)]
    plot("Influence of Host Num", "Host Num", [p for p in range(1, 20)])

def Q8():
    global rates, protocal_names
    rates = [[] for i in range(2)]
    total_simulation = 100
    link_delay_list= [0,1,2,3]
    packet_size_list= [7,5,3,1] # To ensure that the packet_time remains constant.
    for l,p in zip(link_delay_list, packet_size_list):
        t = [[] for i in range(2)]
        setting = Setting(link_delay=l, packet_size=p)  
        for i in range(total_simulation): 
            t[0].append(csma(setting, False))
            t[1].append(csma_cd(setting, False))
        t = [[[t[pro][m][n] for m in range(total_simulation)] for n in range(3)] for pro in range(2)]
        t = [[sum(x)/total_simulation for x in t[pro]] for pro in range(2)]
        for i in range(2): rates[i].append(t[i])
    rates = [[[rates[i][p][r] for p in range(len(rates[i]))] for r in range(3)] for i in range(2)]
    
    tmp = protocal_names
    protocal_names = protocal_names[2:]
    plot("Influence of Link Delay", "Link Delay", [0,1,2,3])
    protocal_names = tmp
    

if __name__ == "__main__":
    test()