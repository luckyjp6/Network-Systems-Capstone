Max_payload = 1000

class QUIC_packet():
    def __init__(self, buf=b''):
        if len(buf) == 0: return
        data = buf.split(' ')
        idx = 0
        self.pn = int(data[idx]); idx += 1
        self.types = data[idx]; idx += 1
        self.payload = ""
        if (self.types == "stream"): self.payload = STREAM_frame(" ".join(data[idx:]))
        elif (self.types == "ack"): self.payload = ACK_frame(" ".join(data[idx:]))
        elif (self.types == "init"): self.payload = INIT_frame(" ".join(data[idx:]))
    
    def set(self, pn, types, payload) -> None:
        self.pn = pn
        self.types = types
        self.payload = payload
        # if (self.types == "stream"): self.payload = STREAM_frame(payload)
        # elif (self.types == "ack"): self.payload = ACK_frame(payload)
        # elif (self.types == "init"): self.payload = INIT_frame(payload)
        return

    def to_string(self) -> str:
        s = ""
        s += str(self.pn) + " "
        s += self.types + " "
        s += self.payload
        return s

class INIT_frame():
    def __init__(self, buf=b''):
        if len(buf) == 0: return
        data = buf.split(',') # ("127.0.0.1",10013)
        self.info = (data[0][2:-1], int(data[1][:-1]))
        # print(self.info)
        return
    
    def set(self, destination):
        self.info = destination
        return
    
    def to_string(self) -> str:
        s = ""
        s += str(self.info)
        return s

class STREAM_frame():
    def __init__(self, data=b'') -> None:
        if len(data) == 0: return
        data = data.split(' ')
        idx = 0
        self.stream_id = int(data[idx]); idx += 1
        self.packet_len = int(data[idx]); idx += 1
        self.fin = int(data[idx]); idx += 1
        self.offset = int(data[idx]); idx += 1
        self.payload = "".join(data[idx:])
        self.payload = self.payload
        return
    
    def set(self, stream_id, packet_len, fin, offset, payload) -> None:
        self.stream_id = stream_id
        self.packet_len = packet_len
        self.fin = fin
        self.offset = offset
        self.payload = payload.decode()
        return
    
    def to_string(self) -> str:
        s = ""
        s += str(self.stream_id) + " "
        s += str(self.packet_len) + " "
        s += str(self.fin) + " "
        s += str(self.offset) + " "
        s += self.payload
        return s

class ACK_frame():
    def __init__(self, data=b''):
        if len(data) == 0: return
        data = data.split(' ')
        self.ack_range = []
        for d in data:
            item = d.split(',')
            self.ack_range.append((int(item[0]), int(item[1])))
        return
        
    
    def set(self, ack_range) -> None:
        self.ack_range = ack_range
        return

    def to_string(self) -> str:
        s = ""
        for ran in self.ack_range:
            s += str(ran[0]) + "," + str(ran[1]) + " "
        return s[:-1]

class MAX_DATA_frame():
    def __init__(self, max_len=0) -> None:
        self.max_len = max_len
        return
    
    def set(self, max_len) -> None:
        self.max_len = max_len
        return
    
    def to_string(self) -> str:
        s = ""
        s += str(self.max_len)
        return s