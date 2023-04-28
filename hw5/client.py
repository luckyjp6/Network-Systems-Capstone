from socket_func import *

class QUICClient:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.pn = 0
        
    def connect(self, socket_addr: tuple[str, int]):
        to_addr = socket_addr
        self.socket.bind(('', 0))

        init_packet = fr.INIT_frame()
        init_packet.set(socket_addr)

        # packet = fr.QUIC_packet()
        # packet.set(0, "init", init_packet.to_string())
        # print("send to {}: {}".format(to_addr, packet.to_string()))
        # self.socket.sendto(packet.to_string().encode(), to_addr)
        send_packet(self.socket, to_addr, 0, "init", init_packet.to_string())

        start_thread(to_addr, self.socket)
        return

    def send(self, stream_id: int, data: bytes):
        self.pn = add_send_queue(self.pn, stream_id, data)
        return
    def recv(self) -> tuple[int, bytes]: # stream_id, data
        global recv_streams, recv_lock
        done_stream = -1
        while done_stream < 0: done_stream = check_done()

        recv_lock.acquire()
        payload = recv_streams[done_stream].get_data()
        recv_streams.pop(done_stream)
        recv_lock.release()

        return done_stream, bytes(payload, 'utf-8')
    def close(self):
        safe_close(self.socket)
        return
    
# if __name__ == "__main__":
#     client = QUICClient()
#     client.connect(("127.0.0.1", 30000))
#     recv_id, recv_data = client.recv()
#     print(recv_data.decode("utf-8")) # SOME DATA, MAY EXCEED 1500 bytes
#     client.send(2, b"Hello Server!")
#     client.close()
if __name__ == "__main__":
    client = QUICClient()
    client.connect(("127.0.0.1", 30000))
    # client.send(0, "test")
    # while(True):
    for i in range(500):
        client.send(i, b'a'*3000)
    for i in range(500):
        # client.send()
        id, payload = client.recv()
        print(id, i)
        # client.recv()
    client.close()