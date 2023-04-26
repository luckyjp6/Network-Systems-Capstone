import socket
import frame_struct as fr

class QUICServer:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cli_addr = ""
        self.conn_id = 0
        self.pn = 0
        
    def listen(self, socket_addr: tuple[str, int]):
        self.socket.bind(socket_addr)
    
    def get_packet(self) -> fr.QUIC_packet:
        packet = ""
        # print(self.socket.recvfrom(50000))#, encoding='utf-8')
        packet, self.cli_addr = self.socket.recvfrom(50000)#, encoding='utf-8')

        packet = str(packet, encoding='utf-8')
        return fr.QUIC_packet(packet)
    def send_packet(self, types, payload):
        packet = fr.QUIC_packet()
        packet.set(self.conn_id, self.pn, types, payload)
        self.socket.sendto(packet.to_string().encode(), self.cli_addr)
        self.pn += 1
        return
        
    def accept(self):
        # self.conn, self.addr = server.accept()
        # get init packet
        init_packet = self.get_packet()
        self.conn_id = init_packet.conn_id
        self.pn = init_packet.pn
        
        return

    def send(self, stream_id: int, data: bytes):
        stream_payload = fr.STREAM_frame()
        stream_payload.set(stream_id, len(data), 1, 0, data)
        self.send_packet("stream", stream_payload.to_string())
        return
    
    def recv(self) -> tuple[int, bytes]: # stream_id, data
        packet = self.get_packet()
        return packet.payload.stream_id, packet.payload.payload

    def close(self):
        self.socket.close()

if __name__ == "__main__":
    server = QUICServer()         
    server.listen(("127.0.0.1", 10013))
    server.accept()
    # while(True):
    for i in range(3):
        server.send(i, 'aaaa')
    #     server.recv()