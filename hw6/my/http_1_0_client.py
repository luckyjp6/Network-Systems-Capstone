import socket
import json
from Utils import Parser
import os
import glob
import xml.etree.ElementTree as ET

class HTTPClient():
    def __init__(self) -> None:
        pass
        
    def __send_request(self, s:socket.socket, request):
        request_str = f"{request['method']} {request['resource']} {request['version']}\r\n"

        for key, value in request['headers'].items():
            request_str += f"{key}: {value}\r\n"
        request_str += "\r\n"
        request_str += request['body']

        s.sendall(request_str.encode())
        
    def get(self, url, headers=None, stream=False):
        request = {
            'version': 'HTTP/1.0', 
            'method':'GET', 
            'scheme':'http',
            'headers': {'Content-Type': 'text/html', 'Content-Length': 0},
            'body': ""
        }
        url = url.replace("http://", "")
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(5)
        host = url.find(":")
        path = url.find("/")
        port = "8080"
        if host >= 0: port = url[host+1:path]
        else: host = path
        host = url[0:host]
        request['authority'] = f"{host}:{port}"
        request['resource'] = url[path:]
        request['path'] = url[path:]
        request['body'] = ""

        # print(f"host: {host}, port: {port}, path: {path}")

        try: self.s.connect((host, int(port)))
        except: 
            print("connec fail")
            return None
        try:
            self.__send_request(self.s, request)
        except:
            print("sendall fail")
            self.s.close()
            return None
        
        # receive response
        # try:
        response = Response(self.s, stream)

        # get header 
        recv_header = b''
        nextline_count = 0
        for i in range(500):
            b = self.s.recv(1)
            recv_header += b
            if b == b'\r': 
                b = self.s.recv(1)
                recv_header += b
                if b == b'\n': nextline_count += 1
            else: nextline_count = 0
            if nextline_count == 2: break
            
        resp_parse = Parser.parse_response(recv_header.decode())
        response.version = resp_parse['version']
        response.status = resp_parse['status']
        response.headers = resp_parse['headers']
        response.body_length = int(resp_parse['headers']['content-length'])

        if not stream: 
            while not response.complete:
                response.get_remain_body()

        return response
    

class Response():
    def __init__(self, socket:socket.socket, stream) -> None:
        self.socket = socket
        self.stream = stream

        # fieleds
        self.version = "" # e.g., "HTTP/1.0"
        self.status = ""  # e.g., "200 OK"
        self.headers = {} # e.g., {content-type: application/json}
        self.body = b""  # e.g. "{'id': '123', 'key':'456'}"
        self.body_length = 0
        self.recv_len = 0
        self.complete = False
    def get_full_body(self): # used for handling short body
        if self.stream or not self.complete:
            return None
        return self.body # the full content of HTTP response body
    def get_stream_content(self): # used for handling long body
        if not self.stream or self.complete:
            return None
        if self.body != b"":
            content = self.body
            self.body = b""
            print(content)
            return content
        content = self.get_remain_body() # recv remaining body data from socket
        return content # the part content of the HTTP response body
    def get_remain_body(self): 
        recv_bytes = self.socket.recv(4096)
        if not self.stream: self.body += recv_bytes
        self.recv_len += len(recv_bytes)

        if self.recv_len >= self.body_length: 
            self.complete = True
            self.socket.close()
        
        return recv_bytes

if __name__ == '__main__':
    client = HTTPClient()

    target_path = "../../target"
    response = client.get(url=f"127.0.0.1:8080/")
    file_list = []
    if response and response.headers['content-type'] == 'text/html':
        root = ET.fromstring(response.body.decode())
        links = root.findall('.//a')
        file_list = []
        for link in links:
            file_list.append(link.text) 

    for file in glob.glob(os.path.join(target_path, '*.txt')):
        os.remove(file)

    for file in file_list:
        response = client.get(f"127.0.0.1:8080/static/{file}", stream=True)
        file_path = f"{target_path}/{file}"
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
    # Send an HTTP GET request to the server
    # request = "GET /get?id=123 HTTP/1.0\r\n\r\n"
    # response = send_reqeuest(request)
    # print(response)
    # headers = response['headers']
    # body = response['body']

    # if 'content-type' in headers and headers['content-type'] == 'application/json':
    #     try:
    #         data = json.loads(body)
    #         if 'id' in data and 'key' in data:
    #             print(f"Get id={data['id']} key={data['key']}")
    #         else:
    #             data = None
    #     except:
    #         data = None
    # else:
    #     data = None
    
    # if data is None:
    #     print('Get failed')
    #     exit()

    # # Send an HTTP POST request to the server
    # request = f"POST /post HTTP/1.0\r\nContent-Type: application/json\r\n\r\n{json.dumps(data)}"
    # response = send_reqeuest(request)
    # print(response)
    # headers = response['headers']
    # body = response['body']
    # if 'content-type' in headers and headers['content-type'] == 'application/json':
    #     try:
    #         data = json.loads(body)
    #         if 'success' in data:
    #             print(f"Post success={data['success']}")
    #         else:
    #             data = None
    #     except:
    #         data = None
    # else:
    #     data = None
    # if not data:
    #     print('Post failed')