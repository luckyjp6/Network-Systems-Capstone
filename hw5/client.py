import socket
import frame_struct as fr
import recv_structure as rs

class QUICClient:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.pn = 0
        self.srv_addr = ""
        self.recv_pn = rs.recv_pn()
        self.recv_streams = dict()
        self.end = False
        
    def connect(self, socket_addr: tuple[str, int]):
        self.srv_addr = socket_addr
        self.socket.connect(socket_addr)
        init_packet = fr.INIT_frame()
        init_packet.set(socket_addr)
        # print(init_packet.info)
        self.send_packet(self.socket, self.pn, "init", init_packet.to_string())
        self.pn += 1
        return
    
    def get_packet(self, s) -> fr.QUIC_packet:
        packet = ""
        try:
            packet, self.cli_addr = s.recvfrom(50000)
        except:
            s.close()
            self.end = True
            exit()
        if len(packet) == 0: return None

        packet = str(packet, encoding='utf-8')
        return fr.QUIC_packet(packet)
    def send_packet(self, s:socket.socket, pn, types, payload):
        packet = fr.QUIC_packet()
        packet.set(pn, types, payload)
        # print("send:", packet.to_string())
        try:
            s.sendto(packet.to_string().encode(), self.srv_addr)
        except:
            s.close()
            # print("broken pipe")
            exit()
        return


    def send(self, stream_id: int, data: bytes):
        stream_payload = fr.STREAM_frame()
        stream_payload.set(stream_id, len(data), 1, 0, data)
        self.send_packet(self.socket, self.pn, "stream", stream_payload.to_string())
        self.pn += 1
        return

    def add_stream_data(self, stream_id, offset, fin, payload):
        # first-time recv
        if stream_id not in self.recv_streams:
            self.recv_streams[stream_id] = rs.recv_data()
        
        # append data
        self.recv_streams[stream_id].add(offset, fin, payload)
    def check_done(self):
        for id, item in self.recv_streams.items():
            if item.is_done(): return id
        return -1

    def recv(self) -> tuple[int, bytes]: # stream_id, data
        # if self.end: exit()
        done_stream = -1
        while done_stream < 0:
            packet = self.get_packet(self.socket)
            if packet.types == "stream":
                # record packet
                self.add_stream_data(packet.payload.stream_id, packet.payload.offset, packet.payload.fin, packet.payload.payload)
                # record pn
                self.recv_pn.add(packet.pn)

                # send ack
                ack_packet = fr.ACK_frame()
                ack_packet.set(self.recv_pn.get_needed())
                self.send_packet(self.socket, self.pn, "ack", ack_packet.to_string())
                self.pn += 1
            done_stream = self.check_done()

        payload = self.recv_streams[done_stream].get_data()
        self.recv_streams.pop(done_stream)
        return done_stream, payload

    def close(self):
        self.socket.close()


if __name__ == "__main__":
    client = QUICClient()
    client.connect(("127.0.0.1", 10013))
    # client.send(0, "test")
    # while(True):
    for i in range(3):
        # client.send()
        print(client.recv())

    client.close()