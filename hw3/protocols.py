import random
from setting import Setting

class my_host():
    def __init__(self, packet, setting):
        self.packet_time = setting.packet_time
        self.backoff_max = setting.max_colision_wait_time
        self.packets = packet
        self.num_packet_sent = 0
        self.num_data_sent = 0
        self.history = ""
        self.action = '.'
        self.retranmit= False
        self.num_backoff = 0 # 還沒做四次backoff就放棄傳送的機制
        self.backoff = 0 
    def check_send(self, time, send_rate):
        if send_rate == 0: self.action = "."
        elif self.num_packet_sent == len(self.packets): self.action = "."
        elif time >= self.packets[self.num_packet_sent]: 
            if self.retranmit: 
                if random.uniform(0, 1) < send_rate: self.action = "s"
            else: self.action = "s"
        else: self.action = "."

    def get_state(self, time, num_send=0, no_cs=False, send_rate=1):
        # if len(self.history) == 0: self.action =  "."
        if self.action == ".":
            # some packet(s) are ready to be sent
            if self.backoff == 0:
                if num_send == 0: self.check_send(time, send_rate)
            else: self.backoff -= 1
        elif self.action == "|":
            self.backoff -= 1
            self.action = "."
            if self.backoff == 0:
                if num_send == 0: self.check_send(time, send_rate)
        elif self.action == "s":
            if num_send > 1: 
                self.action = "|"
                self.num_data_sent = 0
                self.num_backoff += 1
                self.backoff = random.randint(1, self.backoff_max)
            elif self.history[-1] == "-" or self.history[-1] == "<": 
                self.num_data_sent += 1
                self.action = "s"
            elif self.history[-1] == ">":
                # finish sending one packet
                self.num_packet_sent += 1
                self.num_data_sent = 0
                # if there's another packet ready to send
                self.check_send(time, send_rate)
        else: print("unexpected state")
    
    def add_history(self, ack=True):
        if self.action == ".": self.history += "."
        elif self.action == "|":
            if self.history[-1] == "|": self.history += "."
            else: self.history += "|"
        elif self.action == "s":
            if self.num_data_sent == 0: self.history += "<"
            elif self.num_data_sent == self.packet_time-1: 
                if ack: self.history += ">"
                else: 
                    self.num_data_sent = 0
                    self.history += "|"
                    self.action = "|"
                    self.num_backoff += 1
                    self.backoff = random.randint(1, self.backoff_max)
            else: self.history += "-"
        else: self.history += self.action

    def print_history(self, idx, total_time):
        send = list(' ' * total_time)
        for p in self.packets:
            send[p] = "V"

        print("  : {}".format("".join(send)))
        print("h{}: {}".format(idx, self.history))

def check_collision(hosts):
    num = 0
    for host in hosts:
        if host.action == "s": 
            num += 1
        if num > 1: break
        
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
            host.get_state(t, num_send=0, no_cs=True)
        
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
            host.add_history(is_ack)
        
    if show_history:
        # Show the history of each host
        print("ALOHA")
        for idx, host in enumerate(hosts):
            host.print_history(idx, setting.total_time)

    success_rate = 0
    for host in hosts:
        success_rate += host.num_packet_sent
    success_rate *= setting.packet_time

    idle_rate /= setting.total_time
    success_rate /= setting.total_time
    collision_rate = 1 - idle_rate - success_rate
    return success_rate, idle_rate, collision_rate

def slotted_aloha(setting, show_history=False):
    packets = setting.gen_packets()
    hosts = [my_host(packet, setting) for packet in packets]
    success_rate = 0
    idle_rate = 0
    collision_rate = 0
    num_send = [0 for i in range(setting.packet_time)]

    for t in range(setting.total_time):
        # All hosts decide the action (send/idle/stop sending)
        if (t % setting.packet_time != 0): send_rate = 0
        else: send_rate = setting.p_resend
        for host in hosts: host.get_state(t, no_cs=True, send_rate=send_rate)
        
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

    idle_rate /= setting.total_time
    success_rate /= setting.total_time
    collision_rate = 1 - idle_rate - success_rate
    return success_rate, idle_rate, collision_rate
    
def csma(setting, show_history=False):
    packets = setting.gen_packets()
    hosts = [my_host(packet, setting) for packet in packets]
    success_rate = 0
    idle_rate = 0
    collision_rate = 0
    num_send = [0 for i in range(setting.packet_time)]

    for t in range(setting.total_time):
        # All hosts decide the action (send/idle/stop sending)
        for host in hosts: host.get_state(t, num_send = num_send[-1], no_cs=True)
        
        # Hosts that decide to send send packets.
        num_send.append(check_collision(hosts))

        # Check collision if two or above hosts are sending.
        if (num_send[-1] == 0): idle_rate += 1

        for host in hosts:
            host.add_history()
        
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

    idle_rate /= setting.total_time
    success_rate /= setting.total_time
    collision_rate = 1 - idle_rate - success_rate
    return success_rate, idle_rate, collision_rate

def csma_cd(setting, show_history=False):
    return