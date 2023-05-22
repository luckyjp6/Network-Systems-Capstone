import socket
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
            'headers': {'Content-Type': 'text/html'},
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
        response = Response(self.s, stream)

        # get header 
        recv_header = b''
        nextline_count = 0
        while True:
            b = self.s.recv(1)
            recv_header += b
            if b == b'\r': 
                b = self.s.recv(1)
                recv_header += b
                if b == b'\n': nextline_count += 1
            else: nextline_count = 0
            if nextline_count == 2: break
            
        resp_parse = parse_response(recv_header.decode())
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

def parse_response(response_str):
    response = {
        'version': "", # e.g. "HTTP/1.0"
        'status': "", # e.g. "200 OK"
        'headers': {}, # e.g. {content-type: application/json}
        'body': ""  # e.g. "{'id': '123', 'key':'456'}"
    }
    # Split the request into a list of strings
    lines = response_str.split('\r\n')
    if len(lines) < 2:
        return None

    # Split the method, resource and version
    index = lines[0].find(" ")
    if index == -1 or index+1 >= len(lines[0]):
        return None
    
    # Extract method and requested resource
    response['version'] = lines[0][:index]
    response['status'] = lines[0][index+1:]

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

if __name__ == '__main__':
    client = HTTPClient()

    target_path = "../../target"
    response = client.get(url=f"http://127.0.0.1:8080/")
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