import io
import os
import socket
import threading
import struct
import time
from datetime import datetime

class ClientHandler():
    def __init__(self, client, address, static_path) -> None:
        self.client = client
        self.client.settimeout(5)
        self.address = address
        self.alive = True
        self.recv_buffer = b""
        self.recv_streams = {}
        self.send_buffers = {}
        self.static_path = static_path

        self.send_count = 0

        # self.key = hmac_sha256(f'key{random.random()*100}', 'http11')
        self.recv_thread = threading.Thread(target=self.__recv_loop)
        self.recv_thread.start()
        self.send_thread = threading.Thread(target=self.__send_loop)
        self.send_thread.start()

    def __bad_request_response(self):
        response = {
            'version': "HTTP/2.0", # e.g. "HTTP/1.0"
            'status': "400 Bad Request", # e.g. "200 OK"
            'headers': {'Content-Type': 'text/html'}, # e.g. {content-type: application/json}
            'body': "<html><body><h1>400 Bad Request</h1></body></html>"  
        }
        return response
        
    def __not_found_response(self):
        response = {
            'version': "HTTP/2.0", # e.g. "HTTP/1.0"
            'status': "404 Not Found", # e.g. "200 OK"
            'headers': {'Content-Type': 'text/html'}, # e.g. {content-type: application/json}
            'body': "<html><body><h1>404 Not Found</h1></body></html>" 
        }
        return response

    def __do_get(self, request):
        path = request['path']
        params = request['params']
        response = self.__not_found_response()
        if path == "/":
            response['status'] = "200 OK"
            response['headers'] = {'Content-Type': 'text/html', 'Content-Length':574}
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
            try:
                file_size = os.path.getsize(file_name)
                file = io.open(file_name, "r", newline='')
                response['status'] = "200 OK"
                response['headers'] = {'Content-Type': 'text/html', 'Content-Length':file_size}
                
                while True:
                    content = file.read(3000)
                    file_size -= len(content)
                    response['body'] = content
                    self.__send_response(request, response, (file_size == 0))
                    if file_size == 0: break
                file.close()
                return
            except:
                print(f"open {file_name} fail")
                file.close()
                return

    # def __do_post(self, request):
    #     path = request['path']
    #     headers = request['headers']
    #     response = self.__not_found_response()
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
    #     self.__send_response(request, response, complete=True)

    def __send_response(self, request, response, complete):
        response['headers'][':status'] = response['status']
        stream_id = request['stream_id']
        self.__send_headers(stream_id, response['headers'])

        self.__send_body(stream_id, response['body'].encode(), complete)

        # Log
        # print("body len:", len(response['body']))
        print(f"{self.address[0]} - - {datetime.now().strftime('%d/%m/%y %H:%M:%S')} \"{request['method']} {request['path']} {request['version']}\" {response['status']} -")

    def __send_headers(self, stream_id, headers, end_stream=False):
        hdr = ""
        for key, value in headers.items():
            hdr += f"{key}: {value}\r\n"
        frame = create_headers_frame(stream_id, hdr.encode(), end_stream)
        if stream_id in self.send_buffers:
            while len(self.send_buffers[stream_id]) > 0: continue
        self.send_buffers[stream_id] = [frame]

    def __send_body(self, stream_id, body, complete):
        chunk_size = Frame.max_payload_size
        while len(body) > chunk_size:
            frame = create_data_frame(stream_id, body[:chunk_size])
            body = body[chunk_size:]
            self.send_buffers[stream_id].append(frame) 
        frame = create_data_frame(stream_id, body, end_stream=complete)
        self.send_buffers[stream_id].append(frame) 

    def __complete_request(self, stream_id):
        try:
            stream = self.recv_streams[stream_id]
            headers = stream['headers']
            path, params = parse_resource(headers[':path'])
            request = {
                'stream_id': stream_id,
                'method': headers[':method'], # e.g. "GET"
                'path': path, # e.g. "/"
                'params': params, # e.g. {'id': '123'}
                'scheme': headers[':scheme'],
                'version': "HTTP/2.0", # e.g. "HTTP/1.0"
                'headers': stream['headers'], # e.g. {content-type: application/json}
                'body': stream['body'].decode('utf-8')  # e.g. "{'id': params['id'], 'key': hmac_sha256(params['id'], 'http10')}"
            }
        except:
            if stream_id in self.recv_streams:
                del self.recv_streams[stream_id]
            return
        method = request['method']
        # Check the method and path
        if method == "GET":
            self.__do_get(request)
        elif method == "POST":
            self.__do_post(request)
        else:
            self.__send_response(request, self.__bad_request_response(), True)
        
    def __send_loop(self):
        while self.alive:
            end_streams = []
            try:
                keys = list(self.send_buffers.keys())
                # if self.send_buffers: print(self.send_buffers)
                for key in keys:
                    if len(self.send_buffers[key]) > 0:
                        frame = self.send_buffers[key].pop(0)
                        self.client.sendall(frame.to_bytes())
                        if frame.flags == 1:
                            end_streams.append(key)
                for key in end_streams:
                    del self.send_buffers[key]
            except:
                self.alive = False
                self.client.close()
                break

    def __recv_loop(self):
        while self.alive:
            try:
                # Recv request
                recv_bytes = self.client.recv(8192)

                # check connection
                if not recv_bytes:
                    print("client close connection")
                    self.alive = False
                    self.client.close()
                    break

                recv_bytes = self.recv_buffer + recv_bytes

                # parse request
                frames, remian_bytes = bytes_to_frames(recv_bytes)
                self.recv_buffer = remian_bytes
                for frame in frames:
                    # print(f"flags: {frame.flags}, type: {frame.type}, payload: {frame.payload}")
                    if frame.type == 0: # data
                        self.recv_streams[frame.stream_id]['body'] += frame.payload
                    elif frame.type == 1: # header
                        headers = parse_header(frame.payload.decode())
                        self.recv_streams[frame.stream_id] = {
                            'headers': headers,
                            'body': b''
                        }
                    if frame.flags == 1:
                        self.__complete_request(frame.stream_id)
            except:
                self.alive = False
                self.client.close()
                break

    def close(self):
        self.alive = False
        self.client.close()

class HTTPServer():
    def __init__(self, host="127.0.0.1", port=8080) -> None:
        # Create a socket object
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to a specific address and port
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        
        # Listen for incoming connections
        self.socket.listen(5)
        
        # Create a thread to accept clients
        self.thread = threading.Thread(target=self.__accept_loop)

        self.static_path = ""
        self.alive = False
    def set_static(self, path):
        self.static_path = path
    def __accept_loop(self):
        while self.alive:
            try:
                # Establish a connection with the client
                client, address = self.socket.accept()
                client_handler = ClientHandler(client, address, self.static_path)

                for handler in reversed(self.handler_list):
                    if not handler.alive:
                        self.handler_list.remove(handler)
                self.handler_list.append(client_handler)

            except:
                # catch socket closed
                self.alive = False
                pass

    def run(self):
        if not self.alive:
            self.alive = True
            self.handler_list = []
            self.thread.start()

    def close(self):
        self.alive = False
        self.socket.close()
        self.thread.join()
        for handler in reversed(self.handler_list):
            if handler.alive:
                handler.close()

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

def parse_resource(resource):
    # Split resource into path and parameters
    resource = resource.split('?')
    if len(resource) == 2:
        path, parameters = resource
    else:
        return resource[0], {}
    
    # Split the parameters into list
    parameters = parameters.split('&')

    # Initialize an empty dictionary to store the params
    params = {}
    
    # Iterate through the parameters
    for para in parameters:
        # Split the para into a key-value pair
        para = para.split('=')
        if (len(para) == 2):
            key, value = para
            params[key] = value
    return path, params

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

if __name__ == '__main__':
    server = HTTPServer()
    server.set_static("../../static")
    server.run()

    while True:
        cmd = input()
        if cmd == 'close' or cmd == 'exit':
            server.close()
            break