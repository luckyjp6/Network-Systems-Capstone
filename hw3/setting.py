import random
class Setting():
    def __init__(self, host_num=3, total_time=10000, packet_num=500, packet_size=5, max_colision_wait_time=None, p_resend=None, coefficient=8, link_delay=1, seed=None):
        self.host_num = host_num
        self.total_time = total_time # total simulation time
        self.packet_num = packet_num # packet num for each host
        # packet time is the time it takes for a packet to finish transmission, both packet's link delay and ack's link delay are included
        # assume ack transmission time equals to the link delay
        self.packet_time = packet_size + 2*link_delay # the packet time it takes for a packet to finish transmission, equals to slote size of slotted aloha
        self.packet_size = packet_size
        self.max_colision_wait_time = max_colision_wait_time # maximum random backoff time, for aloha, csma, csma/cd
        self.p_resend = p_resend # retransmission rate for slotted aloha
        self.link_delay = link_delay
        
        if seed is None:
            self.seed = random.randint(1, 10000)
        else:
            self.seed = seed
        
        if max_colision_wait_time is None:
            self.max_colision_wait_time = (host_num * packet_size) * coefficient
        else:
            self.max_colision_wait_time = max_colision_wait_time 
        if p_resend is None:
            self.p_resend = (1.0/host_num)/coefficient
        else:
            self.p_resend = p_resend 

    # format
    # e.g.
    #   [[10, 20, 30], # host 0
    #    [20, 30, 50], # host 1
    #    [30, 50, 60]] # host 2
    def gen_packets(self):
        random.seed(self.seed)
        packets = [[] for i in range(self.host_num)]
        for i in range(self.host_num):
            packets[i] = random.sample(range(1, self.total_time-self.packet_size), self.packet_num)
            packets[i].sort()
        return packets