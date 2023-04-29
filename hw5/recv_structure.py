from frame_struct import Max_payload as max_len

class recv_data:
    def __init__(self) -> None:
        self.num = 0
        self.stream_id = []
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
        self.recv = []

    def add(self, pn):
        # already received
        self.recv.append(pn)

    def get_needed(self):
        total_num = len(self.recv)
        if total_num == 0: return 0, None
        
        self.recv.sort()

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
        return total_num, ack