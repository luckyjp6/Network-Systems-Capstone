from setting import get_hosts, get_switches, get_links, get_ip, get_mac

"""
ARP request: <src ip> arp_req <request ip>
ARP reply:   arp_rply <ip>
"""

class host:
    def __init__(self, name, ip, mac):
        self.name = name
        self.ip = ip
        self.mac = mac 
        self.port_to = None 
        self.arp_table = dict() # IP addresses -> MAC addresses
    
    def add(self, node):
        self.port_to = node
                
    def show_table(self):
        # display ARP table entries for this host
        print("---------------{}:".format(self.name))
        for ip, mac in self.arp_table.items():
            print("{}:{}".format(ip, mac))
    
    def clear(self):
        # clear ARP table entries for this host
        self.arp_table.clear()
    
    def update_arp(self, ip, mac):
        # update ARP table with a new entry
        self.arp_table[ip] = mac
    
    def handle_packet(self, src_name, src, dst, msg):
        # handle incoming packets 
        # print("I'm {}".format(self.name))
        slice = msg.split(' ')
        # arp request
        if msg.find("arp_req") >= 0:
            if slice[2] == self.ip:
                self.update_arp(slice[0], src)
                self.send(slice[0], "arp_rply "+self.ip)
        elif msg.find("arp_rply") >= 0:
            self.update_arp(slice[1], src)
    
    def ping(self, dst_ip): 
        # handle a ping request
        while(True): 
            if self.send(dst_ip, "ping"): return            
    
    def send(self, dst, msg):
        # get node connected to this host
        global switch_dict

        node = switch_dict[self.port_to]
        # send packet to the connected node
        if dst in self.arp_table:
            node.handle_packet(self.name, self.mac, self.arp_table[dst], msg)
            return True
        else:
            # ARP, set dst==None -> broadcast
            node.handle_packet(self.name, self.mac, None, self.ip+" arp_req "+dst) 
            return False
        return False

class switch:
    def __init__(self, name, port_n):
        self.name = name
        self.mac_table = dict() # MAC addresses -> port numbers
        self.port_n = port_n # number of ports on this switch
        self.port_to = list() # port -> host name
    
    def add(self, node): 
        # link with other hosts or switches
        self.port_to.append(node)
        self.port_n += 1
    
    def show_table(self):
        # display MAC table entries for this switch
        print("---------------{}:".format(self.name))
        for mac, port in self.mac_table.items():
            print("{}:{}".format(mac, port))
    
    def clear(self):
        # clear MAC table entries for this switch
        self.mac_table.clear()
    
    def update_mac(self, addr, port):
        # update MAC table with a new entry
        self.mac_table[addr] = port
    
    def send(self, port, src, dst, msg): 
        # send to the specified port
        global host_dict, switch_dict

        p = self.port_to[port]
        if p in switch_dict: 
            switch_dict[p].handle_packet(self.name, src, dst, msg)
        elif p in host_dict: 
            host_dict[p].handle_packet(self.name, src, dst, msg)
    
    def get_port(self, name):
        tmp = [i for i in range(len(self.port_to)) if self.port_to[i] == name]
        # print("##", tmp)
        return tmp[0]
    
    def handle_packet(self, src_name, src, dst, msg): # get src and dst MAC address
        # print("I'm {}".format(self.name))
        # handle incoming packets
        src_port = self.get_port(src_name)
        self.update_mac(src, src_port)
        # broadcast
        if dst is None or dst not in self.mac_table:
            # flush
            for i in range(len(self.port_to)):
                if i == src_port: continue
                self.send(i, src, dst, msg)
        else:
            self.send(self.mac_table[dst], src, dst, msg)

def add_link(entries): 
    # create a link between two nodes
    global host_dict, switch_dict

    if (entries[0] in host_dict): host_dict[entries[0]].add(entries[1])
    else: switch_dict[entries[0]].add(entries[1])
    if (entries[1] in host_dict): host_dict[entries[1]].add(entries[0])
    else: switch_dict[entries[1]].add(entries[0])

def set_topology():
    global host_dict, switch_dict

    hostlist = get_hosts().split(' ')
    switchlist = get_switches().split(' ')
    link_command = get_links().split(' ')
    ip_dic = get_ip()
    mac_dic = get_mac()
    
    host_dict = dict() # maps host names to host objects
    switch_dict = dict() # maps switch names to switch objects

    # ... create nodes and links
    for name in hostlist:
        host_dict[name] = host(name, ip_dic[name], mac_dic[name])
    for name in switchlist:
        switch_dict[name] = switch(name, 0)
    for link in link_command:
        l = link.split(',')
        if l[0] not in host_dict and l[0] not in switch_dict: print("invalid link")
        elif l[1] not in host_dict and l[1] not in switch_dict: print("invalid link")                
        else: add_link(l)

def ping(h1, h2): 
    # initiate a ping between two hosts
    global host_dict, switch_dict
    
    node1 = host_dict[h1]
    node2 = host_dict[h2]
    node1.ping(node2.ip)

def show_table(target): 
    # display the ARP or MAC table
    global host_dict, switch_dict
    
    # show an specific target
    if target.find("all") < 0: 
        if target in host_dict: 
            print("ip : mac")
            host_dict[target].show_table()
        if target in switch_dict: 
            print("mac:port")
            switch_dict[target].show_table()
        return
    # show all hosts
    if target.find("_hosts") >= 0:
        print("ip : mac")
        for host in host_dict.values():
            host.show_table()
        return
    # show all switches
    if target.find("_switches") >= 0:
        print("mac:port")
        for switch in switch_dict.values():
            switch.show_table()
        return
    # show everything
    for host in host_dict.values():
        print("ip : mac")
        host.show_table()
    for switch in switch_dict.values():
        print("mac:port")
        switch.show_table()
    return

def clear(target):
    # clear an specific target
    global host_dict, switch_dict
    
    if target.find("all") < 0: 
        if target in host_dict: host_dict[target].clear()
        if target in switch_dict: switch_dict[target].clear()
        return
    # clear all hosts
    if target.find("_hosts") >= 0:
        for host in host_dict.values():
            host.clear()
        return
    # clear all switches
    if target.find("_switches") >= 0:
        for switch in switch_dict.values():
            switch.clear()
        return
    # clear everything
    for host in host_dict.values():
        host.clear()
    for switch in switch_dict.values():
        switch.clear()

def print_err():
    print("a wrong comand")

def run_net():
    global host_dict, switch_dict
    
    while(1):
        command_line = input(">> ")
        slice = command_line.split(' ')
        if command_line.find("ping") >= 0:
            # host1 ping host2
            if len(slice) < 3: print_err()
            elif slice[0] not in host_dict or slice[2] not in host_dict: print_err()
            else: ping(slice[0], slice[2])
        elif command_line.find("show_table") == 0:
            # show_table item
            # show_table all_hosts/all_switches
            if slice[1] not in host_dict and slice[1] not in switch_dict:
                if command_line.find("all") < 0: 
                    print_err()
                    continue
            if len(slice) < 2: show_table("all")
            else: show_table(slice[1])
        elif command_line.find("clear") == 0:
            if len(slice) < 2: clear("all")
            else: clear(slice[1])
        else:
            print_err()
    
def main():
    set_topology()
    run_net()


if __name__ == '__main__':
    main()
