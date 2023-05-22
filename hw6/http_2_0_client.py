import socket
import os
import glob
import threading
import xml.etree.ElementTree as ET
import time
import struct
from collections import deque

class HTTPClient:
    def __init__(self) -> None:
        self.connecting = False
    def get(self, url, headers=None):
        request = {
            'version': 'HTTP/2.0', 
            
            'headers': {':method':'GET', ':scheme':'http', 'Content-Type': 'text/html'},
        }
        url = url.replace("http://", "")
        host = url.find(":")
        path = url.find("/")
        self.port = url[host+1:path]
        self.host = url[0:host]
        request['headers'][':authority'] = f"{self.host}:{self.port}"
        self.port = int(self.port)
        request['headers'][':resource'] = url[path:]
        request['headers'][':path'] = url[path:]
        
        self.connect(self.host, self.port)

        stream_id = self.send_reqeuest(request)

        # self.recv_streams[stream_id] = Response(stream_id)

        return self.recv_streams[stream_id]

    def __get_next_stream_id(self):
        stream_id = self.next_stream_id
        self.next_stream_id += 2
        return stream_id
    
    def connect(self, host="127.0.0.1", port=8080):
        if not self.connecting:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            try:
                self.socket.connect((host, port))
                
                self.connecting = True
                self.recv_buffer = b""
                self.recv_streams = {}
                self.send_buffers = {}
                self.next_stream_id = 1
                self.recv_thread = threading.Thread(target=self.__recv_loop)
                self.recv_thread.start()
                self.send_thread = threading.Thread(target=self.__send_loop)
                self.send_thread.start()
            except:
                self.connecting = False
                self.socket.close()
                print("####cannot connect")

    def __complete_stream(self, stream_id):
        if stream_id in self.recv_streams:
            self.recv_streams[stream_id].complete = True

    def __send_loop(self):
        while self.connecting:
            try:
                end_streams = []
                keys = list(self.send_buffers.keys())
                for key in keys:
                    if len(self.send_buffers[key]) > 0:
                        frame = self.send_buffers[key].pop(0)
                        self.socket.sendall(frame.to_bytes())
                        if frame.flags == 1:
                            end_streams.append(key)
                        time.sleep(0.002)
                for key in end_streams:
                    del self.send_buffers[key]
            except:
                self.connecting = False
                self.socket.close()
                break

    def __recv_loop(self):
        while self.connecting:
            try:
                recv_bytes = self.socket.recv(4096)
                if not recv_bytes:
                    self.connecting = False
                    self.socket.close()
                    break
                recv_bytes = self.recv_buffer + recv_bytes
                # parse request
                frames, remain_bytes = bytes_to_frames(recv_bytes)
                self.recv_buffer = remain_bytes
                for frame in frames:
                    if frame.type == 0: # data
                        # print("recv", len(frame.payload))
                        self.recv_streams[frame.stream_id].contents.append(frame.payload)
                        self.recv_streams[frame.stream_id].recv_len += len(frame.payload)
                        # self.__complete_stream(frame.stream_id)
                    elif frame.type == 1: # header
                        headers = parse_header(frame.payload.decode())
                        if frame.stream_id not in self.recv_streams:
                            print(f"unknown stream id {frame.stream_id}")
                            continue
                        self.recv_streams[frame.stream_id].headers = headers
                        self.recv_streams[frame.stream_id].status = headers[':status']
                        self.recv_streams[frame.stream_id].total_len = int(headers['content-length'])
                        

                    if self.recv_streams[frame.stream_id].check_complete(): 
                        print(f"complete {frame.stream_id}, data: {self.recv_streams[frame.stream_id].headers}")
                        self.__complete_stream(frame.stream_id)
            except:
                self.connecting=False
                self.socket.close()
                break

    def __send_headers(self, stream_id, headers, end_stream=False):
        hdr = ""
        for key, value in headers.items():
            hdr += f"{key}: {value}\r\n"
        frame = create_headers_frame(stream_id, hdr.encode(), end_stream)
        self.send_buffers[stream_id] = [frame]

    def __send_body(self, stream_id, body):
        chunk_size = Frame.max_payload_size
        chunk_size = 1
        while len(body) > chunk_size:
            frame = create_data_frame(stream_id, body[:chunk_size])
            body = body[chunk_size:]
            self.send_buffers[stream_id].append(frame) 
        frame = create_data_frame(stream_id, body, end_stream=True)
        self.send_buffers[stream_id].append(frame) 
        
    def send_reqeuest(self, request):
        if not self.connecting: return None
        stream_id = self.__get_next_stream_id()
        self.recv_streams[stream_id] = Response(stream_id) #{'request': request, 'complete': False, 'headers': '', 'body': b''}
        headers = request['headers']
        if 'body' in request:
            self.__send_headers(stream_id, headers)
            body = request['body']
            self.__send_body(stream_id, body)
        else:
            self.__send_headers(stream_id, headers, end_stream=True)
        return stream_id
        
    def close(self):
        self.connecting = False
        self.socket.close()

def parse_header(data):
    # Split the request into a list of strings
    lines = data.split('\r\n')
    # Initialize an empty dictionary to store the headers
    headers = {}
    # Iterate through the lines
    for line in lines:
        # Skip empty lines
        if line == '':
            break
        # Split the line into a key-value pair
        index = line.find(":",1)
        if index != -1 and index+2<len(line):
            key, value = line[:index].strip(), line[index+1:].strip()
            headers[key.lower()] = value
    return headers


class Response():
    def __init__(self, stream_id, headers = {}, status = "Not yet") -> None:
        self.stream_id = stream_id
        self.headers = headers
        
        self.status = status
        self.body = b""

        self.recv_len = 0
        self.total_len = 0
        self.contents = deque()
        self.complete = False
    
    def check_complete(self) -> bool:
        return self.recv_len >= self.total_len

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
            if self.complete or time.time()-begin_time > 5: # if response is complete or timeout
                return None
        content = self.contents.popleft() # pop content from deque
        return content # the part content of the HTTP response body

class Frame:
    max_payload_size = 16384 # 2^14
    def __init__(self, length=0, type=0, flags=0, r=0, stream_id=0, payload=b"") -> None:
        self.length = length #(24)
        self.type = type #(8)
        self.flags  = flags #(8)
        self.r = r #(1)
        self.stream_id = stream_id #(31)
        self.payload = payload
    
    def to_bytes(self):
        return struct.pack(f"!LBL{self.length}s",
            (self.length << 8) | self.type,
            self.flags,
            (self.r << 31) | self.stream_id,
            self.payload)

def create_data_frame(stream_id, payload, end_stream=False):
    if len(payload) > Frame.max_payload_size: # 2^14-1
        raise "payload can't larger than 2^14-1"
    return Frame(length=len(payload), type=0, flags=end_stream, stream_id=stream_id, payload=payload)

def create_headers_frame(stream_id, payload, end_stream=False):
    if len(payload) > Frame.max_payload_size: # 2^14-1
        raise "payload can't larger than 2^14-1"
    return Frame(length=len(payload), type=1, flags=end_stream, stream_id=stream_id, payload=payload)

def bytes_to_frame(data):
    length_type, = struct.unpack(f"!L", data[:4])
    length = length_type >> 8
    type, flags, r_stream_id, payload = struct.unpack(f"!BBL{length}s", data[3:])
    return Frame(length=length, type=type, flags=flags, r=r_stream_id>>31, stream_id=r_stream_id&((1<<31)-1), payload=payload)

def bytes_to_frames(data):
    frames = []
    remain_bytes = b""
    while len(data) > 0:
        length_type, = struct.unpack(f"!L", data[:4])
        length = length_type >> 8
        if 9+length <= len(data):
            type, flags, r_stream_id, payload = struct.unpack(f"!BBL{length}s", data[3:9+length])
            frame = Frame(length=length, type=type, flags=flags, r=r_stream_id>>31, stream_id=r_stream_id&((1<<31)-1), payload=payload)
            frames.append(frame)
            data = data[9+length:]
        else:
            remain_bytes = data
            break
    return frames, remain_bytes

# def write_file_from_response(file_path, response):
#     if response:
#         print(f"{file_path} begin")
#         with open(file_path, "wb") as f:
#             while True:
#                 content = response.get_stream_content()
#                 if content is None:
#                     break
#                 f.write(content)
#         print(f"{file_path} end")
#     else:
#         print("no response")

def write_file_from_response(file_path, response):
    if response:
        print(f"{file_path} begin")
        with open(file_path, "wb") as f:
            while True:
                content = response.get_stream_content()
                if content is None: break
                # print("get", len(content))
                f.write(content)
        print(f"{file_path} end")
    else:
        print("no response")
        
if __name__ == '__main__':
    client = HTTPClient()

    target_path = "./tutorials/target"
    response = client.get(url=f"127.0.0.1:8080/")
    file_list = []
    if response:
        headers = response.get_headers()
        if headers['content-type'] == 'text/html':
            body = response.get_full_body()
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