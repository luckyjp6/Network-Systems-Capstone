import socket
import frame_struct as fr
import recv_structure as rs
import threading
import time

recv_dict = threading.Lock()
time_to_stop = False
recv_pn = rs.recv_pn()
recv_streams = dict()
class QUICClient:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.pn = 0
        self.svr_addr = ""
        self.end = False
        
    def connect(self, socket_addr: tuple[str, int]):
        self.svr_addr = socket_addr
        self.socket.connect(socket_addr)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        init_packet = fr.INIT_frame()
        init_packet.set(socket_addr)
        # print(init_packet.info)
        self.send_packet(self.pn, "init", init_packet.to_string())
        self.pn += 1

        recv_thread = threading.Thread(target=self.recv_loop)
        recv_thread.start()
        return
    
    def get_packet(self) -> fr.QUIC_packet:
        packet = ""
        try:
            packet= self.socket.recv(50000)
        except:
            return None
            self.socket.close()
            self.end = True
            exit()
        if len(packet) == 0: return None

        if packet == None: return None
        packet = str(packet, encoding='utf-8')
        return fr.QUIC_packet(packet)
    def send_packet(self, pn, types, payload):
        packet = fr.QUIC_packet()
        packet.set(pn, types, payload)
        # print("send:", packet.to_string())
        try:
            self.socket.sendto(packet.to_string().encode(), self.svr_addr)
        except:
            self.socket.close()
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
        global recv_streams
        # first-time recv

        recv_dict.acquire()
        if stream_id not in recv_streams:
            recv_streams[stream_id] = rs.recv_data()
        
        # append data
        recv_streams[stream_id].add(offset, fin, payload)
        recv_dict.release()

    def check_done(self):
        global recv_streams
        recv_dict.acquire()
        for id, item in recv_streams.items():
            if item.is_done(): 
                recv_dict.release()
                return id
        recv_dict.release()
        return -1

    def recv(self) -> tuple[int, bytes]: # stream_id, data
        global recv_streams
        done_stream = -1
        while done_stream < 0: done_stream = self.check_done()

        recv_dict.acquire()
        payload = recv_streams[done_stream].get_data()
        recv_streams.pop(done_stream)
        recv_dict.release()

        return done_stream, payload
    
    def send_ack(self):
        global recv_pn
        # send ack
        ack_packet = fr.ACK_frame()
        acks = recv_pn.get_needed()
        if len(acks) == 0: return
        ack_packet.set(acks)
        self.send_packet(self.pn, "ack", ack_packet.to_string())
        self.pn += 1
        return
    def send_max_data(self, add):
        payload = fr.MAX_DATA_frame(str(add))
        self.send_packet(self.pn, "max_data", payload.to_string())
        self.pn += 1
        return
    
    def recv_loop(self):
        global time_to_stop, recv_pn
        can_ack = False
        num_recv = 0
        self.socket.settimeout(0.01)
        while True:
            packet = self.get_packet()
            if packet == None:
                if time_to_stop: 
                    self.send_ack()
                    self.socket.close()
                    exit()
                if not can_ack: continue
                can_ack = False
                self.send_ack()
                self.send_max_data(num_recv)
                num_recv = 0
                continue
            if packet.types == "stream":
                num_recv += 1
                can_ack = True
                # record packet
                self.add_stream_data(packet.payload.stream_id, packet.payload.offset, packet.payload.fin, packet.payload.payload)
                # record pn
                recv_pn.add(packet.pn)

    def close(self):
        global time_to_stop
        time_to_stop = True
        while threading.active_count() > 1: pass
        self.socket.close()


if __name__ == "__main__":
    client = QUICClient()
    client.connect(("127.0.0.1", 10013))
    # client.send(0, "test")
    # while(True):
    for i in range(800):
        # client.send()
        id, payload = client.recv()
        # print(id, i)
        # client.recv()
    print("out")
    client.close()