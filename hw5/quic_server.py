from socket_func import *

class QUICServer:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.pn = 0
        
    def listen(self, socket_addr: tuple[str, int]):
        self.socket.bind(socket_addr)
        return
    def accept(self):
        # get init packet
        init_packet, to_addr = get_packet(self.socket, need_addr=True)

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
#     server = QUICServer()
#     server.listen(("", 30000))
#     server.accept()
#     server.send(1, b"SOME DATA, MAY EXCEED 1500 bytes")
#     recv_id, recv_data = server.recv()
#     print(recv_data.decode("utf-8")) # Hello Server!
#     server.close() 
if __name__ == "__main__":
    server = QUICServer()
    server.listen(("127.0.0.1", 30000))
    server.accept()
    
    for i in range(10):
        server.send(i, b'a'*1000000)
    for i in range(10):
        id, payload = server.recv()
        print(id, i)

    server.close()