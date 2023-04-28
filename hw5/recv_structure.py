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
        self.lower_bound = -1
        self.recv = []

    def add(self, pn):
        # already received
        if pn < self.lower_bound: return
        if pn in self.recv: return

        self.recv.append(pn)

    def get_needed(self):
        ack = [] # (down, up+1)
        if len(self.recv) == 0: return ack
        self.recv.sort()

        if self.most_lower == None: 
            self.most_lower = min(self.recv)
            self.lower_bound = self.most_lower+1
        else: ack.append((self.most_lower, self.lower_bound))
        
        max_pn = max(self.recv)
        now_idx = 0
        now_len = 0
        for now in range(self.lower_bound-1, max_pn+1):
            pn = self.recv[now_idx]
            if pn != now:
                if now_len > 0: 
                    ack.append((now - now_len, now))
                now_len = 0
            else:
                now_len += 1
                now_idx += 1
                if now == max_pn: ack.append((now - now_len+1, now+1))

        if ack[0][0] == self.lower_bound:
            self.lower_bound = ack[0][1]
            rm_len = ack[0][0] - ack[0][1]
            del self.recv[:rm_len]

        return ack