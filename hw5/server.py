import socket
import time
import frame_struct as fr
import threading

send_dict = threading.Lock()
wait_to_send = dict()
send_socket = ""
allow_to_send = 500
class QUICServer:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.pn = 0
        self.recv_pn = 0
        self.svr_addr = ""
        self.cli_addr = ""
        
    def listen(self, socket_addr: tuple[str, int]):
        self.svr_addr = socket_addr
        self.socket.bind(socket_addr)
        return
    def accept(self):
        # get init packet
        init_packet = self.get_packet(self.socket)
        self.recv_pn = init_packet.pn

        send_thread = threading.Thread(target=self.send_loop)
        send_thread.start()
        return
    
    def get_packet(self, s) -> fr.QUIC_packet:
        packet = ""
        try:
            packet, self.cli_addr = s.recvfrom(50000)
        except:
            return None

        if len(packet) == 0: return None

        packet = str(packet, encoding='utf-8')
        return fr.QUIC_packet(packet)
    def send_packet(self, s, pn, types, payload):
        packet = fr.QUIC_packet()
        packet.set(pn, types, payload)
        try:
            # print("send:", packet.to_string())
            s.sendto(packet.to_string().encode(), self.cli_addr)
        except:
            s.close()
            print("broken pipe")
            exit()
        return
        
    def send(self, stream_id: int, data: bytes):
        global wait_to_send

        num_segment = int(len(data)/fr.Max_payload)+1
        last = len(data) - (num_segment-1)*fr.Max_payload
        offset = 0

        send_dict.acquire()
        for i in range(num_segment):
            fin = int(i == num_segment-1)
            length = last if fin else fr.Max_payload
            stream_payload = fr.STREAM_frame()
            stream_payload.set(stream_id, length, fin, offset, data[offset:offset+length])
            offset += fr.Max_payload
            wait_to_send[self.pn] = stream_payload.to_string()
            self.pn += 1
        send_dict.release()

        return
    def recv(self) -> tuple[int, bytes]: # stream_id, data
        packet = self.get_packet(self.socket)
        return packet.payload.stream_id, packet.payload.payload

    def close(self):
        self.socket.close()
        # time.sleep(2)
        while wait_to_send: continue
        wait_to_send[-1] = "no"
        while threading.active_count() > 1: pass
        return

    def check_end(self, id, idx):
        item = wait_to_send[id]
        if idx+1 == len(item[1]): return len(item[0]) % fr.Max_payload, 1
        else: return fr.Max_payload, 0
    def send_loop(self):
        global wait_to_send, send_socket, allow_to_send
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        send_socket.bind(self.svr_addr)

        now_at = 0
        to_limit = False

        while(True):
            # wait if empty
            while not wait_to_send: continue

            if not to_limit: now_at = 0
            num_send = 0
            to_limit = False

            send_dict.acquire()
            # send every thing
            for pn, frame in wait_to_send.items(): # pn: STREAM_frame.to_string()
                if pn == -1: 
                    send_socket.close()
                    exit()
                if pn >= now_at: 
                    self.send_packet(send_socket, pn,"stream", frame)
                    num_send += 1
                    allow_to_send -= 1
                    now_at = pn
                    if allow_to_send <= 0: 
                        to_limit = True
                        break
            send_dict.release()

            self.recv_reply(num_send)
            
    def recv_reply(self, num_send):
        global wait_to_send, send_socket, allow_to_send

        send_socket.settimeout(0.2)
        packet = self.get_packet(send_socket)

        num_ack = 0
        while (packet != None): 
            if packet.types == "ack":
                acks = packet.payload.ack_range
                # print(acks)
                for ack in acks:
                    for id in range(ack[0], ack[1], -1):
                        send_dict.acquire()
                        if id in wait_to_send: 
                            wait_to_send.pop(id)
                            num_ack += 1
                        send_dict.release()
            elif packet.types == "max_data":
                allow_to_send += packet.payload.max_len

            packet = self.get_packet(send_socket)
        
        if num_send == 0: 
            # print("error")
            allow_to_send /= 2
        if num_ack/num_send < 1: 
            # print("/2")
            allow_to_send/=2
        else: allow_to_send += 75

if __name__ == "__main__":
    # socket.setdefaulttimeout(2)
    server = QUICServer()
    server.listen(("127.0.0.1", 10013))
    server.accept()
    # while(True):
    for i in range(800):
        # if i == 2: continue
        server.send(i, b'a'*3000)
    #     server.recv()

    server.close()