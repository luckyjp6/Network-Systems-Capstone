import socket
import frame_struct as fr

class QUICClient:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.conn_id = 0
        self.pn = 0
    
    def get_packet(self) -> fr.QUIC_packet:
        packet = ""
        packet, self.cliaddr = self.socket.recvfrom(50000)#, encoding='utf-8')
        packet = str(packet, encoding='utf-8')
        print(packet)
        return fr.QUIC_packet(packet)
    def send_packet(self, types, payload):
        packet = fr.QUIC_packet()
        packet.set(self.conn_id, self.pn, types, payload)
        self.socket.sendall(packet.to_string().encode())
        self.pn += 1
        return
    
    def connect(self, socket_addr: tuple[str, int]):
        self.socket.connect(socket_addr)
        init_packet = fr.INIT_frame()
        init_packet.set(socket_addr)
        # print(init_packet.info)
        self.send_packet("init", init_packet.to_string())
        return

    def send(self, stream_id: int, data: bytes):
        stream_payload = fr.STREAM_frame()
        stream_payload.set(stream_id, len(data), 1, 0, data)
        self.send_packet("stream", stream_payload.to_string())
        return

    def recv(self) -> tuple[int, bytes]: # stream_id, data
        packet = self.get_packet()
        # if packet.types == "stream"
        return packet.payload.stream_id, packet.payload.payload

    def close(self):
        self.socket.close()


if __name__ == "__main__":
    client = QUICClient()
    client.connect(("127.0.0.1", 10013))
    client.send(0, "test")
    while(True):
        # client.send()
        client.recv()