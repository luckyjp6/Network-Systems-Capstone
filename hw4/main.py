from testdata import *
infinity = 999
ospf = "ospf"
rip = "rip"
nodes = []
record = []

class node():
    def __init__(self, id, links, protocol_type):
        self.id = id
        self.links = [[999 for i in range(len(links))] for j in range(len(links))]
        self.ids = [0 for i in range(len(links))]
        self.protocol_type = protocol_type
        
        self.origin_link = links.copy()
        self.links[id] = links.copy()
        self.ids[id] = 1
        
        self.new_links = self.links.copy()
        self.new_ids = self.ids.copy()
        self.no_changes = False

    
    def check(self):
        if self.protocol_type == rip: return self.no_changes
        for i in self.ids:
            if i == 0: return False
        return True
    def update(self):
        self.links = self.new_links.copy()
        self.ids = self.new_ids.copy()
        pass

    def flood(self):
        if self.protocol_type == rip and self.no_changes: return
        for i in range(len(self.origin_link)):
            if i == self.id: continue # self
            if self.origin_link[i] == infinity: continue # can't directly reach
            self.send(i)                

    def send(self, dst):
        global nodes
        if self.protocol_type == ospf:
            for i in range(len(self.ids)):
                if self.ids[i] == 0: continue
                nodes[dst].recv(self.id, i, self.links[i])
        elif self.protocol_type == rip:
            nodes[dst].recv(self.id, self.id, self.links[self.id])
        return
    def recv(self, source, original, get_links):
        global record
        if  self.protocol_type == ospf and self.new_ids[original] == 1: return
        self.new_links[original] = get_links.copy()
        self.new_ids[original] = 1
        if self.protocol_type == ospf: record.append((source, original, self.id))
        elif self.protocol_type == rip: record.append((source, self.id))
        return
    def apply(self, i):
        dis = self.links[self.id][i]
        if self.protocol_type == rip: dis = self.origin_link[i]
        for idx in range(len(self.origin_link)):
            if (self.links[self.id][idx] > self.links[i][idx]+dis):
                self.no_changes = False
                self.links[self.id][idx] = self.links[i][idx]+dis        
        return
    def apply_all(self):
        self.no_changes = True
        for i in range(len(self.origin_link)):
            if i == self.id: continue # self
            if self.origin_link[i] == infinity: continue # can't directly reach
            self.apply(i)
        return
    def calcu_ospf(self):
        finish = [0 for i in range(len(self.links[0]))]
        for i in range(len(self.links[0])):
            min_idx = 0
            min_val = infinity
            for idx in range(len(self.links[0])):
                if finish[idx] == 1: continue
                if self.links[self.id][idx] < min_val:
                    min_val = self.links[self.id][idx]
                    min_idx = idx 
            self.apply(min_idx)
            finish[min_idx] = 1
        return

    def my_print(self):
        print(self.id, ":", self.ids)
        return

def my_print():
    global nodes
    for n in nodes: n.my_print()
    print("")
    return
def config(links, protocol_type):
    global nodes
    nodes.clear()
    for i in range(len(links)):
        n = node(i, links[i], protocol_type)
        nodes.append(n)
    return
def flood():
    global nodes
    for n in nodes: 
        n.flood()
    return
def update():
    global nodes
    for n in nodes: n.update()
    return
def check():
    global nodes
    for n in nodes:
        if not n.check(): return False
    return True
def calcu(protocol_type):
    global nodes
    for n in nodes:
        if protocol_type == ospf: n.calcu_ospf()
        elif protocol_type == rip: n.apply_all()
    return
def get_all():
    global nodes
    return [n.links[n.id] for n in nodes]

def run_ospf(link_cost: list) -> tuple[list, list]:
    global record
    total_record = []
    config(link_cost, ospf)

    finish = False
    while (not finish):
        flood()
        update()
        finish = check()

        record.sort()
        total_record += record
        record.clear()

    calcu(ospf)

    return (get_all(), total_record)
    
def run_rip(link_cost: list) -> tuple[list, list]:
    global record
    total_record = []

    config(link_cost, rip)

    finish = False
    while not finish:
        flood()
        update()
        calcu(rip)
        finish = check() # no change -> finish

        record.sort()
        total_record += record
        record.clear()
    
    return (get_all(), total_record)


if __name__ == "__main__":
    # testdata = [
    #     [  0,   2,   5,   1, 999, 999],
    #     [  2,   0,   3,   2, 999, 999],
    #     [  5,   3,   0,   3,   1,   5],
    #     [  1,   2,   3,   0,   1, 999],
    #     [999, 999,   1,   1,   0,   2],
    #     [999, 999,   5, 999,   2,   0]
    # ]
    
    # ans_ospf = (
    #     [[0, 2, 3, 1, 2, 4],
    #     [2, 0, 3, 2, 3, 5],
    #     [3, 3, 0, 2, 1, 3],
    #     [1, 2, 2, 0, 1, 3],
    #     [2, 3, 1, 1, 0, 2],
    #     [4, 5, 3, 3, 2, 0]],
        
    #     [(0, 0, 1), (0, 0, 2), (0, 0, 3),
    #     (1, 1, 0), (1, 1, 2), (1, 1, 3),
    #     (2, 2, 0), (2, 2, 1), (2, 2, 3),
    #     (2, 2, 4), (2, 2, 5), (3, 3, 0),
    #     (3, 3, 1), (3, 3, 2), (3, 3, 4),
    #     (4, 4, 2), (4, 4, 3), (4, 4, 5),
    #     (5, 5, 2), (5, 5, 4), (2, 0, 4),
    #     (2, 0, 5), (2, 1, 4), (2, 1, 5),
    #     (2, 3, 5), (2, 4, 0), (2, 4, 1),
    #     (2, 5, 0), (2, 5, 1), (2, 5, 3)]
    # )
    
    # ans_rip = (
    #     [[0, 2, 3, 1, 2, 4],
    #     [2, 0, 3, 2, 3, 5],
    #     [3, 3, 0, 2, 1, 3],
    #     [1, 2, 2, 0, 1, 3],
    #     [2, 3, 1, 1, 0, 2],
    #     [4, 5, 3, 3, 2, 0]],
        
    #     [(0, 1), (0, 2), (0, 3), (1, 0),
    #     (1, 2), (1, 3), (2, 0), (2, 1),
    #     (2, 3), (2, 4), (2, 5), (3, 0),
    #     (3, 1), (3, 2), (3, 4), (4, 2),
    #     (4, 3), (4, 5), (5, 2), (5, 4),
    #     (0, 1), (0, 2), (0, 3), (1, 0),
    #     (1, 2), (1, 3), (2, 0), (2, 1),
    #     (2, 3), (2, 4), (2, 5), (3, 0),
    #     (3, 1), (3, 2), (3, 4), (4, 2),
    #     (4, 3), (4, 5), (5, 2), (5, 4),
    #     (0, 1), (0, 2), (0, 3), (1, 0),
    #     (1, 2), (1, 3), (2, 0), (2, 1),
    #     (2, 3), (2, 4), (2, 5), (5, 2),
    #     (5, 4)]
    # )
    
    for i in range(2):
        # print(run_ospf(testdata) == ans_ospf)
        # print(run_rip(testdata) == ans_rip)
        print(run_ospf(testdata[i]))
        print(run_rip(testdata[i]))