import random
class my_host():
    def __init__(self, packet, setting):
        self.packet_time = setting.packet_time
        self.backoff_max = setting.max_colision_wait_time
        self.packets = packet
        self.num_packet_sent = 0
        self.num_data_sent = 0
        self.history = ""
        self.action = '.'
        self.retransmit= False
        self.backoff = 0 
        self.is_me = 0
        # random.seed(1)
    
    def get_backoff(self):
        if (self.backoff > 0): return
        self.backoff = random.randint(1, self.backoff_max)
    
    def check_send(self, time):        
        if self.num_packet_sent == len(self.packets): return False # packet all sent
        # if there's any packet ready to be sent
        return time >= self.packets[self.num_packet_sent]

    def do_idle(self, time, num_send, send_rate):
        if self.backoff > 0: self.backoff -=1 # update backoff
        if send_rate == -1: return # for slotted_aloha, check if at the start of a slot
        if self.check_send(time): # check if there's any packet ready to be sent
            if (random.uniform(0,1) < send_rate) and self.retransmit: # for slotted_aloha, retransmit for prob. p
                self.action = "s" 
                return
            if self.backoff > 0: return # backoff -> do not send packet
            if num_send == 1 and self.is_me > 0: 
                self.action = "s"
                self.is_me = 0
            elif num_send > 0:
                self.get_backoff() # for csma&csma_cd sence channel busy -> backoff
                return
            else: self.action = "s"          
    def do_collision(self):
        self.action = "|"
        self.retransmit = True
        self.num_data_sent = 0 # reset sending packet
        self.get_backoff()

    def get_state(self, time, num_send=0, send_rate=0, cd=False):
        if self.is_me > 0: self.is_me -= 1 # update is_me
        if self.action == ".": self.do_idle(time, num_send, send_rate)
        elif self.action == "|":
            self.action = "."
            self.do_idle(time, num_send, send_rate)
        elif self.action == "s" or self.action == "a":
            if cd and (num_send > 1): 
                self.do_collision() # for csma/cd
                return
            self.num_data_sent += 1
            if self.num_data_sent == self.packet_time-1: self.action = "a"
        else: print("unexpected state")
    
    def add_history(self, delay=0, ack=True):
        if self.action == "s":
            if self.num_data_sent == 0: self.history += "<"                
            else: self.history += "-"
        elif self.action == "a":
            if ack: 
                # finish sending one packet
                self.num_data_sent = 0
                self.num_packet_sent += 1
                self.retransmit = False
                self.history += ">"
                self.action = "."
                if delay > 0: self.is_me = delay+1+1
            else: 
                self.history += "|"
                self.do_collision()
        else: self.history += self.action
    def print_history(self, idx, total_time):
        send = list(' ' * total_time)
        for p in self.packets:
            send[p] = "V"

        print("    {}".format("".join(send)))
        print("h{}: {}".format(idx, self.history))

def check_collision(hosts):
    num = 0
    for host in hosts:
        if host.action == "s" or host.action == "|": 
            num += 1
        if num > 1: return num        
    return num

def aloha(setting, show_history=False):
    packets = setting.gen_packets()
    hosts = [my_host(packet, setting) for packet in packets]
    success_rate = 0.0
    idle_rate = 0.0
    collision_rate = 0.0
    num_send = [0 for i in range(setting.packet_time)]

    for t in range(setting.total_time):
        # All hosts decide the action (send/idle/stop sending)
        for host in hosts: 
            host.get_state(t)
        
        # Hosts that decide to send send packets.
        num_send.append(check_collision(hosts))

        # Check collision if two or above hosts are sending.
        if (num_send[-1] == 0): idle_rate += 1.0

        for host in hosts:
            is_ack = True
            for i in range(0, setting.packet_time):
                if num_send[-i] > 1:
                    is_ack = False
                    break
            host.add_history(ack=is_ack)
        
    if show_history:
        # Show the history of each host
        print("ALOHA")
        for idx, host in enumerate(hosts):
            host.print_history(idx, setting.total_time)

    success_rate = 0
    for host in hosts:
        success_rate += host.num_packet_sent
    success_rate *= setting.packet_time
    collision_rate = setting.total_time - idle_rate - success_rate

    idle_rate /= setting.total_time
    success_rate /= setting.total_time
    collision_rate /= setting.total_time
    return success_rate, idle_rate, collision_rate

def slotted_aloha(setting, show_history=False):
    packets = setting.gen_packets()
    hosts = [my_host(packet, setting) for packet in packets]
    success_rate = 0.0
    idle_rate = 0.0
    collision_rate = 0.0
    num_send = [0 for i in range(setting.packet_time)]

    for t in range(setting.total_time):
        # All hosts decide the action (send/idle/stop sending)
        if (t % setting.packet_time != 0): send_rate = -1
        else: send_rate = setting.p_resend
        for host in hosts: host.get_state(t, send_rate=send_rate)
        
        # Hosts that decide to send send packets.
        num_send.append(check_collision(hosts))

        # Check collision if two or above hosts are sending.
        if (num_send[-1] == 0): idle_rate += 1

        for host in hosts:
            is_ack = (num_send[-1] == 1)
            host.add_history(ack=is_ack)
        
    if show_history:
        # Show the history of each host
        print("slotted_ALOHA")
        for idx, host in enumerate(hosts):
            host.print_history(idx, setting.total_time)
        print("")

    success_rate = 0
    for host in hosts:
        success_rate += host.num_packet_sent
    success_rate *= setting.packet_time
    collision_rate = setting.total_time - idle_rate - success_rate

    idle_rate /= setting.total_time
    success_rate /= setting.total_time
    collision_rate /= setting.total_time
    return success_rate, idle_rate, collision_rate
    
def csma(setting, show_history=False):
    packets = setting.gen_packets()
    hosts = [my_host(packet, setting) for packet in packets]
    success_rate = 0.0
    idle_rate = 0.0
    collision_rate = 0.0
    num_send = [0 for i in range(setting.packet_time)]

    for t in range(setting.total_time):
        # All hosts decide the action (send/idle/stop sending)
        for host in hosts: host.get_state(t, num_send=num_send[-setting.link_delay-1])
        
        # Hosts that decide to send send packets.
        num_send.append(check_collision(hosts))

        # Check collision if two or above hosts are sending.
        if (num_send[-1] == 0): idle_rate += 1

        for host in hosts:
            is_ack = True
            for i in range(1, setting.packet_time):
                if num_send[-i] > 1:
                    is_ack = False
                    break
            host.add_history(delay=setting.link_delay, ack=is_ack)
        
    if show_history:
        # Show the history of each host
        print("csma")
        for idx, host in enumerate(hosts):
            host.print_history(idx, setting.total_time)
        print("")

    success_rate = 0
    for host in hosts:
        success_rate += host.num_packet_sent
    success_rate *= setting.packet_time
    collision_rate = setting.total_time - idle_rate - success_rate

    idle_rate /= setting.total_time
    success_rate /= setting.total_time
    collision_rate /= setting.total_time
    return success_rate, idle_rate, collision_rate

def csma_cd(setting, show_history=False):
    packets = setting.gen_packets()
    hosts = [my_host(packet, setting) for packet in packets] #, is_binary_backoff=True
    success_rate = 0.0
    idle_rate = 0.0
    collision_rate = 0.0
    num_send = [0 for i in range(setting.packet_time)]

    for t in range(setting.total_time):
        # All hosts decide the action (send/idle/stop sending)
        for host in hosts: host.get_state(t, num_send = num_send[-setting.link_delay-1], cd=True)
        
        # Hosts that decide to send send packets.
        num_send.append(check_collision(hosts))

        # Check collision if two or above hosts are sending.
        if (num_send[-1] == 0): idle_rate += 1

        for host in hosts:
            host.add_history(delay=setting.link_delay)
        
    if show_history:
        # Show the history of each host
        print("csma_cd")
        for idx, host in enumerate(hosts):
            host.print_history(idx, setting.total_time)
        # print("".join(map(str, num_send[1:])))

    success_rate = 0
    for host in hosts:
        success_rate += host.num_packet_sent
    success_rate *= setting.packet_time
    collision_rate = setting.total_time - idle_rate - success_rate

    idle_rate /= setting.total_time
    success_rate /= setting.total_time
    collision_rate /= setting.total_time
    return success_rate, idle_rate, collision_rate