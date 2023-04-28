from frame_struct import Max_payload as max_len

class recv_data:
    def __init__(self) -> None:
        self.num = 0
        self.data = []
        return
    
    def add(self, offset, fin, data):
        idx = int(offset/max_len)
        loss = idx - len(self.data)
        if loss >= 0:
            for i in range(loss): self.data.append("")
            self.data.append(data)
        else:
            # already received
            if len(self.data[idx]) > 0: return
            else:
                self.data[idx] = data
        
        # increase counter
        self.num += 1

        # set fin
        if fin: self.num -= (idx+1)
        
        return
    
    def is_done(self):
        return ((len(self.data) > 0) and (self.num == 0))
    
    def get_data(self):
        s = ""
        for d in self.data: s += d
        return s
    
class recv_pn:
    def __init__(self) -> None:
        self.most_lower = None
        self.lower_bound = None
        self.upper_bound = None
        self.recv = []

    def add(self, pn):
        # already received
        if pn in self.recv: return False
        if self.lower_bound != None:
            if pn >= self.most_lower and pn < self.lower_bound: return False

        self.recv.append(pn)
        return True

    def get_needed(self):
        ack = [] # (down, up+1)
        if len(self.recv) == 0: 
            if self.most_lower != None: return [(self.most_lower, self.lower_bound)]
            else: return ack
        self.recv.sort()

        if self.most_lower == None: 
            self.most_lower = min(self.recv)
            self.lower_bound = self.most_lower
        # else: ack.append((self.most_lower, self.lower_bound+1))
        
        self.upper_bound = max(self.recv)
        now_idx = 0
        now_len = 0
        for now in range(self.lower_bound, self.upper_bound+1):
            pn = self.recv[now_idx]
            if pn != now:
                if now_len > 0: 
                    ack.append((now - now_len, now))
                now_len = 0
            else:
                now_len += 1
                now_idx += 1
                if now == self.upper_bound: ack.append((now - now_len+1, now+1))
        # print("")
        # print("lower bound", self.lower_bound, self.recv, ack)
        if len(ack) > 0:
            if ack[0][0] == self.lower_bound:
                self.lower_bound = ack[0][1]
                rm_len = ack[0][1] - ack[0][0]
                del self.recv[:rm_len]
                del ack[0]
            ack.append((self.most_lower, self.lower_bound))
        # else: ack.append((self.most_lower, self.lower_bound))
        # print("lower bound", self.lower_bound, self.recv, ack)
        # print("")
        return ack