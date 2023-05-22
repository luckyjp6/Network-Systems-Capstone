import threading
from datetime import datetime
# import json
import io
import socket
import os
# from hashlib import sha256
# import hmac
# import base64
# import random
# from Utils import Parser
from struct import pack, unpack
import math, time

# def hmac_sha256(data, key):
#     key = key.encode('utf-8')
#     message = data.encode('utf-8')
#     sign = base64.b64encode(hmac.new(key, message, digestmod=sha256).digest())
#     sign = str(sign, 'utf-8')
#     return sign
now = lambda: time.time()

class ClientHandler():
    def __init__(self, client, address, static_path) -> None:
        self.client = client
        self.address = address
        self.static_path = static_path
        self.alive = True
        # self.key = hmac_sha256(f'key{random.random()*100}', 'http11')
        self.recv_thread =  threading.Thread(target=self.__recv_loop)
        self.recv_thread.start()

    def __bad_request_response(self):
        response = {
            'version': "HTTP/3.0", 
            'status': "400 Bad Request",
            'headers': {'Content-Type': 'text/html'},
            'body': "<html><body><h1>400 Bad Request</h1></body></html>"  
        }
        return response
        
    def __not_found_response(self):
        response = {
            'version': "HTTP/3.0", 
            'status': "404 Not Found",
            'headers': {'Content-Type': 'text/html', ':status': "404 Not Found"},
            'body': "<html><body><h1>404 Not Found</h1></body></html>" 
        }
        return response

    def __do_get(self, request):
        path = request['path']
        response = self.__not_found_response()
        if path == "/":
            response['status'] = "200 OK"
            response['headers'] = {'Content-Type': 'text/html', 'Content-Length':574, ':status': '200 OK'}
            response['body'] = "<html> \
                                    <header> \
                                    </header> \
                                    <body> \
                                        <a href=\"/static/file_00.txt\">file_00.txt</a> \
                                        <br/> \
                                        <a href=\"/static/file_01.txt\">file_01.txt</a> \
                                        <br/> \
                                        <a href=\"/static/file_02.txt\">file_02.txt</a> \
                                    </body> \
                                </html>"
            self.__send_response(request, response, True)
            return
        elif path[:7] == "/static": # get file from directory "/static"
            file_name = self.static_path + path[7:]
            # print(f"request {file_name}")
            # try:
            file_size = os.path.getsize(file_name)
            file = io.open(file_name, "r", newline='')
            response['status'] = "200 OK"
            response['headers'] = {'Content-Type': 'text/html', 'Content-Length':file_size}
            
            while True:
                content = file.read(3000)
                file_size -= len(content)
                response['body'] = content
                self.__send_response(request, response, file_size == 0)
                if file_size == 0: break
                response.clear()
            file.close()
            return
            # except:
            #     print(f"open {file_name} fail")
            #     file.close()
            #     return

    # def __do_post(self, request):
    #     path = request['path']
    #     headers = request['headers']
    #     response = self.__not_found_response()
    #     print(request)
    #     if path == "/post":
    #         if 'content-type' in headers and headers['content-type'] == 'application/json':
    #             try:
    #                 post_data = json.loads(request['body'])
    #             except:
    #                 post_data = None
    #         else:
    #             post_data = None
    #         if post_data:
    #             if 'id' in post_data and 'key' in post_data and post_data['key'] ==  self.key:
    #                 response['status'] = "200 OK"
    #                 response["headers"] = {'Content-Type': 'application/json'}
    #                 response['body'] = json.dumps({'success':True})
    #                 print(post_data['id'], "success")
    #             else:
    #                 response['status'] = "200 OK"
    #                 response["headers"] = {'Content-Type': 'application/json'}
    #                 response['body'] = json.dumps({'success':False})
    #                 print(post_data['id'], "fail")
    #         else:
    #             response = self.__bad_request_response()
    #     self.__send_response(request, response)

    def __send_response(self, request, response, complete):
        stream_id = request['stream_id']
        response_str = ""
        if 'headers' in response:
            response_str += f"{response['version']} {response['status']}\r\n"
            for key in response['headers']:
                response_str += f"{key}: {response['headers'][key]}\r\n"
            if 'body' in response: response_str += "\r\n"

        response_str += f"{response['body']}"

        self.client.send(stream_id, response_str.encode(), end=complete)

        # Log
        print(f"{self.address[0]} - - {datetime.now().strftime('%d/%m/%y %H:%M:%S')} \"{request['method']} {request['path']} {request['version']}\"")

    def __recv_loop(self):
        while self.alive:
            try:
                # Recv request
                stream_id, recv_bytes, complete = self.client.recv()

                # check connection
                if not stream_id:
                    self.close()
                    break

                # parse request
                request = parse_request(recv_bytes.decode())
                if request == None:
                    method = ""
                else:
                    method = request['method']
                request["stream_id"] = stream_id
                # Check the method and path
                if method == "GET":
                    self.__do_get(request)
                # elif method == "POST":
                #     self.__do_post(request)
                else:
                    self.__send_response(request, self.__bad_request_response(), True)

                # keep connection: don't close socket

            except:
                print("recv except")
                self.alive = False
                self.client.close()
                break

    def close(self):
        self.alive = False
        self.client.close()

def parse_request(request_str):
    request = {
        'method': "", # e.g. "GET"
        'path': "", # e.g. "/"
        'version': "", # e.g. "HTTP/3.0"
        'authority': "",
        'scheme':"",
        'headers': {}, # e.g. {content-type: application/json}
        'body': ""  # e.g. "{'id': '123', 'key':'456'}"
    }
    # Split the request into a list of strings
    lines = request_str.split('\r\n')

    # Split the method, resource and version
    request_list = lines[0].split(' ')
    
    # Extract method and requested resource
    request['method'] = request_list[0]
    request['path'] = request_list[1]
    request['version'] = request_list[2]

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
    request['headers'] = headers

    # Extract the body (if any)
    body = ""
    if "\r\n\r\n" in request_str:
        body = request_str.split("\r\n\r\n")[1]
    request['body'] = body

    return request

class HTTPServer():
    def __init__(self, host="127.0.0.1", port=8080) -> None:
        # Create a socket object
        self.socket = QUICServer(host, port)
        # self.socket.drop(5)
        self.host = host
        self.port = port
        self.handler = None
        self.static_path = ""
        self.alive = False

    def set_static(self, path):
        self.static_path = path
    def __accept_loop(self):
        while self.alive:
            try:
                if self.handler is None:
                    # Establish a connection with the client
                    self.socket.accept()
                    
                    client_handler = ClientHandler(self.socket, self.socket.client_addr, self.static_path)

                    self.handler = client_handler
                if self.handler and not self.handler.alive:
                    self.handler = None
                    self.socket = QUICServer(self.host, self.port)
                    # self.socket.drop(5)
                time.sleep(0.01)

            except:
                # catch socket closed
                pass


    def run(self):
        if not self.alive:
            self.alive = True
            self.handler = None
            # Create a thread to accept clients
            self.thread = threading.Thread(target=self.__accept_loop)
            self.thread.start()

    def close(self):
        if self.alive:
            self.alive = False
            self.socket.close()
            self.thread.join()
            if self.handler:
                self.handler.close()

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

class Pointer:
    def __init__(self, v=0) -> None:
        self.v = v

    def __add__(self, other):
        self.v += other
        return self.v

    def lookahead(self, v):
        return self.v + v

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

class QUICServer:
    def __init__(self, host, port) -> None:
        self.client_addr = None

        # quic
        self.send_wait_list = []
        self.sender_window = Buffer(size=4)
        self.ssthresh = 32
        self.no_resend_list = []
        self.recv_window = {}
        self.recv_window_limit = 16
        self.recv_stream_length = {}
        self.recv_stream_offsets = {}
        self.recv_read_ptr = {}
        self.send_offsets = {}
        self.finished_stream = []
        self.pkt_num = 1
        self.slow_start = True

        # threading
        self.is_running = True
        self.send_manager = threading.Thread(target=self.send_task)
        self.receive_manager = threading.Thread(target=self.recv_task)
        self.meter_manager = threading.Thread(target=self.meter_task)

        # testing
        self.drop_id = []

        # meter
        self.byte_counter = 0

        self.listen((host, port))
    
    def drop(self, stream_id):
        self.drop_id.append(stream_id)
    def listen(self, sockaddr):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(5)
        self.sock.bind(sockaddr)

    def accept(self):
        # expect client init packet
        data, sockaddr = self.sock.recvfrom(1500)
        pkt = Packet()
        pkt.deserialize(data)
        # check if is init packet
        assert pkt.header.header_form == 1
        assert pkt.header.packet_type == 0x00
        if pkt.frame.type == Frame.MAX_DATA:
            self.sender_window.size = pkt.frame.max_data
        # set client addr
        self.client_addr = sockaddr

        # send back init packet
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

        # create thread
        self.send_manager.daemon = True
        self.receive_manager.daemon = True
        self.meter_manager.daemon = True
        self.send_manager.start()
        self.receive_manager.start()
        # self.meter_manager.start()

    def send(self, stream_id, data, end=False):
        pkt = Packet()

        if type(stream_id) == list and type(data) == list:
            stream_id_data = {}
            for i, id in enumerate(stream_id):
                if id in self.drop_id: continue
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
            if stream_id in self.drop_id: return
            if stream_id not in self.send_offsets.keys():
                self.send_offsets[stream_id] = 0
            i = 0
            while i < len(data):
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
        # cc = 0
        while self.is_running:
            # move queue packet to sender window to send
            while not self.sender_window.is_full() and len(self.send_wait_list) != 0:
                self.sender_window.get_buf().append(self.send_wait_list.pop(0))

            halve = False
            for i, (pkt_num, b, t) in enumerate(self.sender_window.get_buf()):
                if t == 0.0 or now() - t > 1.0:
                    if now() - t > 1.0:
                        halve = True
                    self.sender_window.get_buf()[i] = (pkt_num, b, now())
                    self.sock.sendto(b, self.client_addr)

            if halve:
                self.sender_window.halve_size()
                self.slow_start = False

            while len(self.no_resend_list) != 0:
                self.sock.sendto(self.no_resend_list.pop(0), self.client_addr)

    def recv_task(self):
        pkt = Packet()
        reply = Packet()
        while self.is_running:
            try:
                b, addr = self.sock.recvfrom(1500)
            except:
                self.close()
                break
            self.byte_counter += len(b)
            pkt.deserialize(b)
            assert pkt.header.header_form == 0
            if pkt.frame.type == Frame.ACK:
                pkt_num_to_del = pkt.frame.first_ack_range
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

    def meter_task(self):
        while self.is_running:
            self.byte_counter = 0
            time.sleep(1)

    def recv(self):
        # if not self.is_running:
        #     return None, None
        # while len(self.finished_stream) == 0:
        #     pass
        # stream_id = self.finished_stream.pop(0)
        # del self.recv_stream_length[stream_id]
        # data = b''.join(self.recv_window.pop(stream_id))
        # return stream_id, data

        # print(self.recv_window)
        while self.is_running:
            keys = list(self.recv_window.keys())
            for k in keys:
                try:
                    part = self.recv_window[k][self.recv_read_ptr[k]]
                    if part:
                        if self.recv_read_ptr[k] == len(self.recv_window[k]) - 1  and \
                        k in self.finished_stream:
                            del self.recv_stream_length[k]
                            del self.recv_window[k]
                            return k, part, True
                        else:
                            self.recv_read_ptr[k] += 1
                            return k, part, False
                except:
                    pass
        return None, None, False

    def close(self):
        self.is_running = False
        self.send_wait_list.clear()
        self.sender_window._buf.clear()
        self.sender_window.size = 4
        self.no_resend_list.clear()
        self.recv_window.clear()
        self.recv_stream_length.clear()
        self.recv_stream_offsets.clear()
        self.finished_stream.clear()
        self.sock.close()
    
    def pkt_num_inc(self):
        r = self.pkt_num
        self.pkt_num += 1
        return r

if __name__ == '__main__':
    server = HTTPServer()
    server.set_static("../../static")
    server.run()

    while True:
        cmd = input()
        if cmd == 'close' or cmd == 'exit':
            server.close()
            break