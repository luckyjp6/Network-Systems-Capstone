import socket
import threading
import os
import glob
import xml.etree.ElementTree as ET
# import json
import math, time
# from Utils import Frame
# from Utils import Parser
# from QUIC import quic_client
from collections import deque
from struct import pack, unpack

now = lambda: time.time()

class Buffer:
    def __init__(self, size) -> None:
        self.size = size
        self._buf = []

    def get_buf(self):
        return self._buf

    def is_full(self):
        return len(self._buf) == self.size

    def get_size(self):
        return self.size

    def double_size(self):
        self.size += self.size

    def halve_size(self):
        self.size = self.size // 2

    def add_size(self):
        self.size += 1
class Pointer:
    def __init__(self, v=0) -> None:
        self.v = v

    def __add__(self, other):
        self.v += other
        return self.v

    def lookahead(self, v):
        return self.v + v
class Frame:
    PADDING = 0x00
    PING = 0x01
    ACK = 0x02
    STREAM = 0x08 | 0x04 | 0x02
    FIN = 0x01
    MAX_DATA = 0x10
    DATA_BLOCKED = 0x14
    CONNECTION_CLOSE = 0x1c
    HANDSHAKE_DONE = 0x1e

    PKT_NUM_LEN = 0b11
    STREAM_ID_LEN = 8
    OFFSET_LEN = 8
    LENGTH_LEN = 8

    def __init__(self) -> None:
        self.type = None
        self.largest_ack = None
        self.ack_delay = 0
        self.ack_range_count = 0
        self.first_ack_range = 0
        self.ack_range = 0
        self.stream_id = None
        self.offset = None
        self.length = None
        self.stream_data = None
        self.max_data = None
        self.error_code = None
        self.frame_type = None
        self.reason_phrase_len = None
        self.reason_phrase = None
        self.directional = 0x00

    def serialize(self):
        if self.type == Frame.PADDING or self.type == Frame.PING or self.type == Frame.HANDSHAKE_DONE:
            body = pack("!B", self.type)
        elif self.type == Frame.ACK:
            body = pack(f"!B{Frame.PKT_NUM_LEN+1}sBB{Frame.PKT_NUM_LEN+1}s",
                        self.type,
                        self.largest_ack.to_bytes(Frame.PKT_NUM_LEN+1, "big"),
                        self.ack_delay,
                        self.ack_range_count,
                        self.first_ack_range.to_bytes(Frame.PKT_NUM_LEN+1, "big"))
        elif self.type == Frame.STREAM or self.type == Frame.STREAM | Frame.FIN:
            body = pack(f"!B{Frame.STREAM_ID_LEN}s{Frame.OFFSET_LEN}s{Frame.LENGTH_LEN}s",
                        self.type,
                        (self.stream_id | (self.directional << 62)).to_bytes(Frame.STREAM_ID_LEN, "big"),
                        self.offset.to_bytes(Frame.OFFSET_LEN, "big"),
                        self.length.to_bytes(Frame.LENGTH_LEN, "big"))
            body += self.stream_data
        elif self.type == Frame.MAX_DATA or self.type == Frame.DATA_BLOCKED:
            body = pack(f"!B8s", self.type, self.max_data.to_bytes(8, "big"))
        elif self.type == Frame.CONNECTION_CLOSE:
            body = pack(f"!B8sB8s{self.reason_phrase_len}s",
                        self.type,
                        self.error_code.to_bytes(8, "big"),
                        self.frame_type,
                        self.reason_phrase_len.to_bytes(8, "big"),
                        bytes(self.reason_phrase))

        return body

    def deserialize(self, pkt):
        ptr = Pointer()
        (self.type, ) = unpack("!B", pkt[ptr+0:ptr+1])
        if self.type == Frame.ACK:
            (self.largest_ack,
            self.ack_delay,
            self.ack_range_count,
            self.first_ack_range) = unpack(f"!{Frame.PKT_NUM_LEN+1}sBB{Frame.PKT_NUM_LEN+1}s", pkt[ptr+0:])

            self.largest_ack = int.from_bytes(self.largest_ack, "big")
            self.first_ack_range = int.from_bytes(self.first_ack_range, "big")

        elif self.type == Frame.STREAM or self.type == Frame.STREAM | Frame.FIN:
            (stream_id,
            self.offset,
            self.length) = unpack(f"!{Frame.STREAM_ID_LEN}s{Frame.OFFSET_LEN}s{Frame.LENGTH_LEN}s", pkt[ptr+0:ptr+(Frame.STREAM_ID_LEN+Frame.OFFSET_LEN+Frame.LENGTH_LEN)])

            stream_id = int.from_bytes(stream_id, "big")
            self.stream_id = stream_id & (~(3 << 62))
            self.offset = int.from_bytes(self.offset, "big")
            self.length = int.from_bytes(self.length, "big")

            self.stream_data = pkt[ptr+0:]

        elif self.type == Frame.MAX_DATA or self.type == Frame.DATA_BLOCKED:
            (self.max_data, ) = unpack("!8s", pkt[ptr+0:])
            self.max_data = int.from_bytes(self.max_data, "big")

        elif self.type == Frame.CONNECTION_CLOSE:
            (self.error_code,
            self.frame_type,
            self.reason_phrase_len) = unpack("!8sB8s", pkt[ptr+0:ptr+(8+1+8)])

            self.error_code = int.from_bytes(self.error_code, "big")
            self.reason_phrase_len = int.from_bytes(self.reason_phrase_len, "big")

            (self.reason_phrase, ) = unpack(f"!{self.reason_phrase_len}s", pkt[ptr+0:])
            self.reason_phrase = self.reason_phrase.decode("utf-8")

    def clear(self):
        self.__init__()

    def __repr__(self) -> str:
        r_str = ""
        if self.type == Frame.ACK:
            r_str += f", ACK, largest_ack={self.largest_ack} {self.first_ack_range=}"
        elif self.type == Frame.MAX_DATA:
            r_str += f", MAX_DATA, max_data={self.max_data}"
        elif self.type == Frame.STREAM:
            r_str += f", STREAM, {self.stream_id=}, {self.offset=}, {self.length=}"
        elif self.type == Frame.STREAM | Frame.FIN:
            r_str += f", STREAM, FIN, {self.stream_id=}, {self.offset=}, {self.length=}"
        elif self.type == Frame.HANDSHAKE_DONE:
            r_str += f", HANDSHAKE_DONE"
        return r_str
class Header:
    def __init__(self) -> None:
        self.header_form: int = 0 # 1 bit
        self.packet_type: int = 0 # 2 bits
        self.pkt_num_len: int = 0b11 # 2 bit
        self.version: int = 1 # 32 bits
        self.dst_id_len = 20 # 8 bits
        self.dst_id: int = 0 # 160 bits
        self.src_id_len: int = 20 # 8 bits
        self.src_id: int = 0 # 160 bits
        self.length: int = 0 # 62 bits
        self.pkt_num: int = 0 # 32 bits
        self.payload_len: int = 0

    def serialize(self):
        if self.header_form == 1:
            # long header
            first_byte = (self.header_form << 7) +\
                         (1 << 6) +\
                         (self.packet_type << 4) +\
                         self.pkt_num_len

            self.length = 4 + self.payload_len

            hdr = pack(f"!BLB{self.dst_id_len}sB{self.src_id_len}s8s{self.pkt_num_len+1}s",
                       first_byte,
                       self.version,
                       self.dst_id_len,
                       self.dst_id.to_bytes(self.dst_id_len, "big"),
                       self.src_id_len,
                       self.src_id.to_bytes(self.src_id_len, "big"),
                       (self.length | (0b11 << 62)).to_bytes(8, "big"),
                       self.pkt_num.to_bytes(self.pkt_num_len+1, "big"))

        elif self.header_form == 0:
            # short header
            first_byte = 0x40 + self.pkt_num_len

            hdr = pack(f"!B{self.dst_id_len}s{self.pkt_num_len+1}s",
                       first_byte,
                       self.dst_id.to_bytes(self.dst_id_len, "big"),
                       self.pkt_num.to_bytes(self.pkt_num_len+1, "big"))

        else:
            hdr = None

        return hdr

    def deserialize(self, pkt):
        ptr = Pointer()
        (first_byte, ) = unpack("!B", pkt[ptr+0:ptr+1])
        self.header_form = (first_byte & 0x80) >> 7
        if self.header_form == 1:
            # long header
            self.packet_type = (first_byte & 0x30) >> 4
            self.pkt_num_len = first_byte & 0x03

            self.version, self.dst_id_len, self.dst_id, self.src_id_len, self.src_id = unpack(
                    f"!LB{self.dst_id_len}sB{self.src_id_len}s",
                    pkt[ptr+0:ptr+(4+1+self.dst_id_len+1+self.src_id_len)]
                )
            assert self.dst_id_len == 20
            assert self.src_id_len == 20
            self.dst_id = int.from_bytes(self.dst_id, "big")
            self.src_id = int.from_bytes(self.src_id, "big")

            self.length, self.pkt_num = unpack(f"!8s{self.pkt_num_len+1}s", pkt[ptr+0:ptr+(8+self.pkt_num_len+1)])
            self.length = int.from_bytes(self.length, "big")
            self.length &= (~(0b11 << 62))
            self.pkt_num = int.from_bytes(self.pkt_num, "big")

        elif self.header_form == 0:
            # short header
            self.pkt_num_len = first_byte & 0x03
            assert self.dst_id_len == 20
            (self.dst_id, self.pkt_num) = unpack(
                f"!{self.dst_id_len}s{self.pkt_num_len+1}s",
                pkt[ptr+0:ptr+(self.dst_id_len+self.pkt_num_len+1)])
            self.dst_id = int.from_bytes(self.dst_id, "big")
            self.pkt_num = int.from_bytes(self.pkt_num, "big")
        
        return ptr.v

    def clear(self):
        self.__init__()

    def __repr__(self) -> str:
        return_str = ""
        if self.header_form == 1:
            return_str += "long header"
            if self.packet_type == 0x00:
                return_str += ", init packet"
            return_str += f", dst_id={self.dst_id}, src_id={self.src_id}, pkt_num={self.pkt_num}"
        elif self.header_form == 0:
            return_str += f"short header, dst_id={self.dst_id}, pkt_num={self.pkt_num}"
        return return_str

class Packet:
    def __init__(self, hdr=None, frm=None) -> None:
        if not hdr:
            hdr = Header()
        if not frm:
            frm = Frame()
        self.header = hdr
        self.frame = frm

    def serialize(self):
        return self.header.serialize() + self.frame.serialize()

    def deserialize(self, pkt):
        self.clear()
        header_end = self.header.deserialize(pkt)
        self.frame.deserialize(pkt[header_end:])

    def clear(self):
        self.header.clear()
        self.frame.clear()

    def __repr__(self) -> str:
        return str(self.header) + str(self.frame)

def parse_response(response_str):
    response = {
        'version': "", # e.g. "HTTP/3.0"
        'status': "", # e.g. "200 OK"
        'headers': {}, # e.g. {content-type: application/json}
        'body': ""  # e.g. "{'id': '123', 'key':'456'}"
    }
    # Split the request into a list of strings
    lines = response_str.split('\r\n')

    # Split the method, resource and version
    response_list = lines[0].split(" ")
    
    # Extract method and requested resource
    response['version'] = response_list[0]
    response['status'] = response_list[1]

    # Initialize an empty dictionary to store the headers
    headers = {}

    # Iterate through the lines
    for line in lines[1:]:
        # Skip empty lines
        if line == '':
            break
        # Split the line into a key-value pair
        index = line.find(":",1)
        if index != -1 and index+2<len(line):
            key, value = line[:index].strip(), line[index+1:].strip()
            headers[key.lower()] = value
    response['headers'] = headers

    # Extract the body (if any)
    body = ""
    if "\r\n\r\n" in response_str:
        body = response_str.split("\r\n\r\n")[1]
    response['body'] = body
    return response

class HTTPClient:
    def __init__(self) -> None:
        self.connecting = False
        self.recv_streams = {}

    def get(self, url, headers=None):
        request = {
            'headers': {
                'method':'GET',
                'path': '',
                'version': 'HTTP/3.0', 
                'authority': '',
                'scheme':'http',
                'Content-Type': 'text/html'
            },
        }
        url = url.replace("http://", "")
        host = url.find(":")
        path = url.find("/")
        self.port = url[host+1:path]
        self.host = url[0:host]
        request['headers']['authority'] = f"{self.host}:{self.port}"
        self.port = int(self.port)
        request['headers']['path'] = url[path:]
        
        self.connect(self.host, self.port)

        stream_id = self.send_reqeuest(request)

        return self.recv_streams[stream_id]

    def __get_next_stream_id(self):
        stream_id = self.next_stream_id
        self.next_stream_id += 2
        return stream_id
    
    def connect(self, host="127.0.0.1", port=8080):
        if not self.connecting:
            self.socket = QUICClient()
            try:
                self.socket.connect((host, port))
                
                self.connecting = True
                self.recv_buffer = b""
                self.recv_streams = {}
                self.next_stream_id = 1
                self.recv_thread = threading.Thread(target=self.__recv_loop)
                self.recv_thread.start()
            except:
                print("connection failed")
                self.connecting = False
                self.socket.close()

    def __recv_loop(self):
        while self.connecting:
            try:
                stream_id, recv_bytes, complete = self.socket.recv()
                if not stream_id:
                    # print("recv loop not stream id")
                    self.connecting = False
                    self.socket.close()
                    break
                # parse response
                if self.recv_streams[stream_id].status == "Not yet":
                    response = parse_response(recv_bytes.decode())
                    self.recv_streams[stream_id].headers = response['headers']
                    self.recv_streams[stream_id].status = response['status']
                    self.recv_streams[stream_id].contents.append(response['body'].encode())
                else:
                    self.recv_streams[stream_id].contents.append(recv_bytes)
                self.recv_streams[stream_id].complete = complete
            except:
                # print("recv loop fail")
                self.connecting=False
                self.socket.close()
                break
        
    def send_reqeuest(self, request):
        if not self.connecting:
            print("not connecting")
            return None
        stream_id = self.__get_next_stream_id()
        
        data = f"{request['headers']['method']} {request['headers']['path']} {request['headers']['version']}\r\n"

        for key, value in request['headers'].items():
            data += f"{key}: {value}\r\n"
        
        if 'body' in request: data += f"\r\n{request['body']}"

        self.socket.send(stream_id, data.encode())
        self.recv_streams[stream_id] = Response(stream_id)
        return stream_id
        
    def close(self):
        self.connecting = False
        self.socket.close()
        
class Response():
    def __init__(self, stream_id, headers = {}, status = "Not yet") -> None:
        self.stream_id = stream_id
        self.headers = headers
        
        self.status = status
        self.body = b""
        
        self.contents = deque()
        self.complete = False
        
    def get_headers(self):
        begin_time = time.time()
        while self.status == "Not yet":
            if time.time() - begin_time > 5:
                return None
        return self.headers
    
    def get_full_body(self): # used for handling short body
        begin_time = time.time()
        while not self.complete:
            if time.time() - begin_time > 5:
                return None
        if len(self.body) > 0:
            return self.body
        while len(self.contents) > 0:
            self.body += self.contents.popleft()
        return self.body # the full content of HTTP response body
    def get_stream_content(self): # used for handling long body
        begin_time = time.time()
        while len(self.contents) == 0: # contents is a buffer, busy waiting for new content
            if time.time()-begin_time > 30: # if response is complete or timeout
                return None
            if self.complete and len(self.contents) == 0: 
                return None
        content = self.contents.popleft() # pop content from deque
        return content # the part content of the HTTP response body

class QUICClient:
    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(5)
        self.sock.bind(("", 0))
        self.server_addr = None

        # quic
        self.send_wait_list = []
        self.sender_window = Buffer(size=4)
        self.ssthresh = 32
        self.no_resend_list = []
        self.recv_window = {}
        self.recv_window_limit = 16
        self.recv_stream_length = {}
        self.recv_stream_offsets = {}
        self.send_offsets = {}
        self.recv_read_ptr = {}
        self.finished_stream = []
        self.pkt_num = 1
        self.slow_start = True

        # testing
        self.drop_id = []

        # threading
        self.is_running = True
        self.send_manager = threading.Thread(target=self.send_task)
        self.receive_manager = threading.Thread(target=self.recv_task)

    def connect(self, sockaddr):
        self.server_addr = sockaddr

        # build init packet
        pkt = Packet()
        pkt.header.header_form = 1
        pkt.header.packet_type = 0x00
        pkt.header.dst_id = 0
        pkt.header.src_id = 0
        pkt.header.length = 5
        pkt.header.pkt_num = self.pkt_num_inc()
        pkt.header.payload_len = 1
        pkt.frame.type = Frame.MAX_DATA
        pkt.frame.max_data = self.recv_window_limit
        dat = pkt.serialize()

        self.sock.sendto(dat, sockaddr)

        # wait for server's init
        data, sockaddr = self.sock.recvfrom(1500)
        pkt.deserialize(data)
        # check is init packet
        assert pkt.header.header_form == 1
        assert pkt.header.packet_type == 0x00
        if pkt.frame.type == Frame.MAX_DATA:
            self.sender_window.size = pkt.frame.max_data


        # self.send_manager.daemon = True
        # self.receive_manager.daemon = True
        self.send_manager.start()
        self.receive_manager.start()

        # create thread

    def send(self, stream_id, data, end=False):
        pkt = Packet()

        if type(stream_id) == list and type(data) == list:
            stream_id_data = {}
            for i, id in enumerate(stream_id):
                ptr = 0
                stream_id_data[id] = []
                while ptr <= len(data[i]):
                    stream_id_data[id].append((ptr, data[i][ptr:min(ptr+1400, len(data[i]))]))
                    ptr += 1400

            while all([len(datas) != 0 for datas in stream_id_data.values()]):
                for id, datas in stream_id_data.items():
                    if len(datas) != 0:
                        offset, data = datas.pop(0)
                        pkt.clear()
                        pkt.header.header_form = 0
                        pkt.header.pkt_num = self.pkt_num_inc()
                        pkt.header.dst_id = 0
                        pkt.frame.type = Frame.STREAM if len(datas) != 0 else Frame.STREAM | Frame.FIN
                        pkt.frame.stream_id = id
                        pkt.frame.offset = offset
                        pkt.frame.stream_data = data
                        pkt.frame.length = len(pkt.frame.stream_data)
                        b = pkt.serialize()
                        self.send_wait_list.append((pkt.header.pkt_num, b, 0.0))

                    
        elif type(stream_id) == int and type(data) == bytes:
            if stream_id not in self.send_offsets.keys():
                self.send_offsets[stream_id] = 0
            i = 0
            while i <= len(data):
                pkt.clear()
                pkt.header.header_form = 0
                pkt.header.pkt_num = self.pkt_num_inc()
                pkt.header.dst_id = 0
                if end:
                    pkt.frame.type = Frame.STREAM if i + 1400 < len(data) else Frame.STREAM | Frame.FIN
                else:
                    pkt.frame.type = Frame.STREAM
                pkt.frame.stream_id = stream_id
                pkt.frame.offset = i + self.send_offsets[stream_id]
                pkt.frame.stream_data = data[i:min(i+1400, len(data))]
                pkt.frame.length = len(pkt.frame.stream_data)
                b = pkt.serialize()
                self.send_wait_list.append((pkt.header.pkt_num, b, 0.0))

                i += 1400
                
            self.send_offsets[stream_id] += i

    def send_task(self):
        while True:
            # move queue packet to sender window to send
            while not self.sender_window.is_full() and len(self.send_wait_list) != 0:
                self.sender_window.get_buf().append(self.send_wait_list.pop(0))

            halve = False
            for i, (pkt_num, b, t) in enumerate(self.sender_window.get_buf()):
                if t == 0.0 or now() - t > 1.0:
                    if now() - t > 1.0:
                        halve = True
                    self.sender_window.get_buf()[i] = (pkt_num, b, now())
                    self.sock.sendto(b, self.server_addr)

            if halve:
                self.sender_window.halve_size()
                self.slow_start = False
            
            while len(self.no_resend_list) != 0:
                self.sock.sendto(self.no_resend_list.pop(0), self.server_addr)

            if not self.is_running:
                if len(self.no_resend_list) == 0:
                    break

    def recv_task(self):
        pkt = Packet()
        reply = Packet()
        # cc = 0
        while self.is_running:
            try:
                b, addr = self.sock.recvfrom(1500)
                # cc += len(b)
                # print(cc)
            except OSError:
                # print("os error")
                self.is_running = False
                break
            pkt.deserialize(b)
            assert pkt.header.header_form == 0
            if pkt.frame.type == Frame.ACK:
                pkt_num_to_del = pkt.frame.first_ack_range
                pkt_largest_del = pkt.frame.largest_ack
                for i, (pkt_num, _, _) in enumerate(self.sender_window.get_buf()):
                    if pkt_num == pkt_num_to_del:
                        del self.sender_window.get_buf()[i]

                # congestion control
                if self.slow_start:
                    self.sender_window.double_size()
                else:
                    self.sender_window.add_size()
                if self.sender_window.get_size() >= self.ssthresh:
                    self.slow_start = False

            elif pkt.frame.type == Frame.STREAM or pkt.frame.type == Frame.STREAM | Frame.FIN:
                id = pkt.frame.stream_id
                if id in self.drop_id:
                    continue
                # new stream
                if id not in self.recv_window:
                    self.recv_window[id] = []
                    self.recv_stream_offsets[id] = []
                    self.recv_read_ptr[id] = 0
                
                now_pos = math.ceil(pkt.frame.offset / 1400)

                # bypass same packet
                if pkt.frame.offset in self.recv_stream_offsets.get(id):
                    reply.clear()
                    reply.header.header_form = 0
                    reply.header.pkt_num = self.pkt_num_inc()
                    reply.frame.type = Frame.ACK
                    reply.frame.largest_ack = pkt.header.pkt_num
                    reply.frame.first_ack_range = pkt.header.pkt_num
                    b = reply.serialize()
                    self.no_resend_list.append(b)
                    continue
                else:
                    self.recv_stream_offsets[id].append(pkt.frame.offset)

                # reordering
                if len(self.recv_window[id]) == now_pos:
                    # ordered
                    self.recv_window[id].append(pkt.frame.stream_data)
                elif len(self.recv_window[id]) < now_pos:
                    # laters arrived earlier
                    left = now_pos - len(self.recv_window[id])
                    for i in range(left):
                        self.recv_window[id].append(None)
                    self.recv_window[id].append(pkt.frame.stream_data)
                else:
                    # earlies arrived later
                    self.recv_window[id][now_pos] = pkt.frame.stream_data

                # the last frame
                if pkt.frame.type == Frame.STREAM | Frame.FIN:
                    self.recv_stream_length[id] = now_pos + 1
                
                # check frame finish
                for id, pieces in self.recv_stream_length.items():
                    if len(self.recv_window[id]) == pieces and \
                            id not in self.finished_stream and \
                            None not in self.recv_window[id]:
                        self.finished_stream.append(id)
                # reply ACK
                reply.clear()
                reply.header.header_form = 0
                reply.header.pkt_num = self.pkt_num_inc()
                reply.frame.type = Frame.ACK
                reply.frame.largest_ack = pkt.header.pkt_num
                reply.frame.first_ack_range = pkt.header.pkt_num
                b = reply.serialize()
                self.no_resend_list.append(b)

            elif pkt.frame.type == Frame.CONNECTION_CLOSE:
                print("connection close")
                self.is_running = False
                self.sock.close()
        # print("stop running")

    def recv(self):
        # if not self.is_running:
        #     return None, None
        # while len(self.finished_stream) == 0:
        #     pass
        # stream_id = self.finished_stream.pop(0)
        # del self.recv_stream_length[stream_id]
        # data = b''.join(self.recv_window.pop(stream_id))
        # return stream_id, data

        while self.is_running:
            keys = list(self.recv_window.keys())
            for k in keys:
                try:
                    part = self.recv_window[k][self.recv_read_ptr[k]]
                    if part:
                        if self.recv_read_ptr[k] == len(self.recv_window[k]) - 1  and k in self.finished_stream:
                            del self.recv_stream_length[k]
                            del self.recv_window[k]
                            return k, part, True
                        else:
                            self.recv_read_ptr[k] += 1
                            return k, part, False
                except:
                    pass
        return None, None, False


    def drop(self, stream_id):
        self.drop_id.append(stream_id)

    def close(self):
        # print("been closed")
        self.is_running = False
        try:
            self.socket.shutdown(0)
        except:
            pass
        self.sock.close()

        self.send_wait_list.clear()
        self.sender_window._buf.clear()
        self.sender_window.size = 4
        self.no_resend_list.clear()
        self.recv_window.clear()
        self.recv_stream_length.clear()
        self.recv_stream_offsets.clear()
        self.finished_stream.clear()
        
    def pkt_num_inc(self):
        r = self.pkt_num
        self.pkt_num += 1
        return r


def write_file_from_response(file_path, response):
    if response:
        print(f"{file_path} begin")
        with open(file_path, "wb") as f:
            while True:
                content = response.get_stream_content()
                if content is None:
                    break
                f.write(content)
        print(f"{file_path} end")
    else:
        print("no response")
     

if __name__ == '__main__':
    client = HTTPClient()

    target_path = "../../target"
    response = client.get(url=f"http://127.0.0.1:8080/")
    file_list = []
    if response:
        headers = response.get_headers()
        if not headers:
            exit()
        if headers['content-type'] == 'text/html':
            body = response.get_full_body()
            if not body:
                exit()
            root = ET.fromstring(body.decode())
            links = root.findall('.//a')
            file_list = []
            for link in links:
                file_list.append(link.text) 
                
    for file in glob.glob(os.path.join(target_path, '*.txt')):
        os.remove(file)

    th_list = []
    for file in file_list:
        response = client.get(f"127.0.0.1:8080/static/{file}")
        th = threading.Thread(target=write_file_from_response, args=[f"{target_path}/{file}", response])
        th_list.append(th)
        th.start()
        
    for th in th_list:
        th.join()