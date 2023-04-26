class QUIC_packet():
    def __init__(self, buf=""):
        if len(buf) == 0: return
        data = buf.split(' ')
        idx = 0
        self.conn_id = int(data[idx]); idx += 1
        self.pn = int(data[idx]); idx += 1
        self.types = data[idx]; idx += 1
        self.payload = ""
        if (self.types == "stream"): self.payload = STREAM_frame(" ".join(data[idx:]))
        elif (self.types == "ack"): self.payload = ACK_frame("".join(data[idx:]))
        elif (self.types == "init"): self.payload = INIT_frame("".join(data[idx:]))
    
    def set(self, conn_id, pn, types, payload) -> None:
        self.conn_id = conn_id
        self.pn = pn
        self.types = types
        self.payload = ""
        if (self.types == "stream"): self.payload = STREAM_frame(payload)
        elif (self.types == "ack"): self.payload = ACK_frame(payload)
        elif (self.types == "init"): self.payload = INIT_frame(payload)
        return

    def to_string(self) -> str:
        s = ""
        s += str(self.conn_id) + " "
        s += str(self.pn) + " "
        s += self.types + " "
        s += self.payload.to_string()
        return s

class INIT_frame():
    def __init__(self, buf=""):
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
    def __init__(self, data="") -> None:
        if len(data) == 0: return
        data = data.split(' ')
        idx = 0
        self.stream_id = int(data[idx]); idx += 1
        self.packet_len = int(data[idx]); idx += 1
        self.fin = int(data[idx]); idx += 1
        self.offset = int(data[idx]); idx += 1
        self.payload = "".join(data[idx:])
        return
    
    def set(self, stream_id, packet_len, fin, offset, payload) -> None:
        self.stream_id = stream_id
        self.packet_len = packet_len
        self.fin = fin
        self.offset = offset
        self.payload = payload
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
    def __init__(self, data=""):
        if len(data) == 0: return
        data = data.split(' ')
        idx = 0
        self.largest_pn = int(data[idx]); idx += 1
        self.delay = int(data[idx]); idx += 1
        self.ack_range = int(data[idx]); idx += 1
        self.first_range = int(data[idx]); idx += 1
        return
    
    def set(self, largest_pn, delay, ack_range, first_range) -> None:
        self.largest_pn = largest_pn
        self.delay = delay
        self.ack_range = ack_range
        self.first_range = first_range
        return

    def to_string(self) -> str:
        s = ""
        s += str(self.largest_pn) + " "
        s += str(self.delay) + " "
        s += str(self.ack_range) + " "
        s += str(self.first_range)
        return s

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