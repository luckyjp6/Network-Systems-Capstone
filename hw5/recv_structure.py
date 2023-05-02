from frame_struct import Max_payload as max_len

class recv_data:
    def __init__(self) -> None:
        self.num = 0
        self.stream_id = []
        self.data = []
        self.data_size = 0
        return
    
    def add(self, offset, fin, data):
        idx = int(offset/max_len)
        data_len = len(self.data)
        loss = idx - data_len
        if loss >= 0:
            for i in range(loss): self.data.append("")
            self.data.append(data)
        else:
            if len(self.data[idx]) > 0: return # already received
            else:
                self.data[idx] = data
        
        # increase counter
        self.num += 1
        self.data_size += len(data)

        # set fin
        if fin: self.num -= (idx+1)
        
        return
    
    def is_done(self):
        return ((len(self.data) > 0) and (self.num == 0))
    
    def get_data(self):
        s = ""
        for d in self.data: s += d
        return s
    def get_size(self):
        return self.data_size
    
class recv_pn:
    def __init__(self) -> None:
        self.recv = []
        self.max_pn = 100

    def add(self, pn):
        # already received
        self.recv.append(pn)

    def get_needed(self):
        total_num = len(self.recv)
        if total_num == 0: return 0, self.max_pn, None
        
        self.recv.sort()
        self.max_pn = max(self.recv)

        ack = [] # (down, up+1)
        start = min(self.recv)
        prev = start
        for p in self.recv:
            if p <= prev + 1: 
                prev = p
                continue
            else:
                ack.append((start, prev+1))
                start = p
                prev = p
        ack.append((start, prev+1))
        self.recv.clear()
        return total_num, self.max_pn, ack