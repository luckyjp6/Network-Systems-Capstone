import socket
import threading
import io
import os
from datetime import datetime


class ClientHandler():
    def __init__(self, client, address, static_path) -> None:
        self.client = client
        self.client.settimeout(5)
        self.address = address
        self.static_path = static_path
        self.alive = True
        self.recv_thread = threading.Thread(target=self.__recv_loop)
        self.recv_thread.start()

    def __bad_request_response(self):
        response = {
            'version': "HTTP/1.0", 
            'status': "400 Bad Request", 
            'headers': {'Content-Type': 'text/html'},
            'body': "<html><body><h1>400 Bad Request</h1></body></html>"
        }
        return response
    def __not_found_response(self):
        response = {
            'version': "HTTP/1.0", 
            'status': "404 Not Found", 
            'headers': {'Content-Type': 'text/html'}, 
            'body': "<html><body><h1>404 Not Found</h1></body></html>"
        }
        return response

    def __do_get(self, request):
        path = request['path']
        # params = request['params']
        response = self.__not_found_response()
        if path == "/":
            response['status'] = "200 OK"
            response["headers"] = {'Content-Type': 'text/html', 'Content-Length':574}
            response['body'] = "<html> \
                                    <header> \
                                    </header> \
                                    <body> \
                                        <a href=\"/static/file_00.txt\">file_00.txt</a> \
                                        <br/> \
                                        <a href=\"/static/file_02.txt\">file_02.txt</a> \
                                        <br/> \
                                        <a href=\"/static/file_01.txt\">file_01.txt</a> \
                                    </body> \
                                </html>"
            self.__send_response(request, response)
            return            
        elif path[:7] == "/static": # get file from directory "/static"
            file_name = self.static_path + path[7:]
            try:
                file_size = os.path.getsize(file_name)
                file = io.open(file_name, "r", newline='')
            except:
                print(f"open {file_name} fail")
                file.close()
                return
            response['status'] = "200 OK"
            response['headers'] = {'Content-Type': 'text/html', 'Content-Length':file_size}
            
            while True:
                content = file.read(3000)
                if len(content) == 0: break
                response['body'] = content
                if 'headers' in response: self.__send_response(request, response)
                else: self.client.sendall(content.encode())
                response.clear()
            file.close()
            return

    def __send_response(self, request, response):
        response_str = f"{response['version']} {response['status']}\r\n"

        for key, value in response['headers'].items():
            response_str += f"{key}: {value}\r\n"
        response_str += f"\r\n{response['body']}"

        self.client.sendall(response_str.encode())

        # Log
        print(f"{self.address[0]} - - {datetime.now().strftime('%d/%m/%y %H:%M:%S')} \"{request['method']} {request['path']} {request['version']}\" {response['status']} -")

    def __recv_loop(self):
        try:
            # Recv request
            recv_bytes = self.client.recv(4096)

            # check connection
            if recv_bytes == "":
                self.alive = False
                self.client.close()
                return

            # parse request
            request = parse_reqeust(recv_bytes.decode())
            if request == None:
                method = ""
            else:
                method = request['method']
            # Check the method and path
            if method == "GET":
                self.__do_get(request)
            else:
                self.__send_response(request, self.__bad_request_response())

            # Close the connection with the client
            self.client.close()
        except:
            self.alive = False

    def close(self):
        self.alive = False
        self.client.close()

class HTTPServer():
    def __init__(self, host="127.0.0.1", port=8080) -> None:
        # Create a socket object
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to a specific address and port
        self.socket.bind((host, port))
        
        # Listen for incoming connections
        self.socket.listen(5)
        
        # Create a thread to accept clients
        self.thread = threading.Thread(target=self.__accept_loop)

        self.static_path = ""
        self.alive = False

    def __accept_loop(self):
        while self.alive:
            try:
                # Establish a connection with the client
                client, address = self.socket.accept()
                
                client_handler = ClientHandler(client, address, self.static_path)

            except:
                # catch socket closed
                self.alive = False

    def set_static(self, path):
        self.static_path = path

    def run(self):
        if not self.alive:
            self.alive = True
            self.thread.start()

    def close(self):
        self.alive = False
        self.socket.close()
        self.thread.join()
        
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
def parse_reqeust(request_str):
    request = {
        'method': "", # e.g. "GET"
        'path': "", # e.g. "/"
        'params': {}, # e.g. {'id': '123'}
        'version': "", # e.g. "HTTP/1.0"
        'headers': {}, # e.g. {content-type: application/json}
        'body': ""  # e.g. "{'id': '123', 'key':'456'}"
    }
    # Split the request into a list of strings
    lines = request_str.split('\r\n')
    if len(lines) < 2:
        return None

    # Split the method, resource and version
    request_list = lines[0].split()
    if len(request_list) != 3:
        return None
    
    # Extract method and requested resource
    request['method'] = request_list[0]
    resource = request_list[1]
    request['version'] = request_list[2]

    request['path'], request['params'] = parse_resource(resource)

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

if __name__ == '__main__':
    server = HTTPServer()
    server.set_static("../static")
    server.run()

    while True:
        cmd = input()
        if cmd == 'close' or cmd == 'exit':
            server.close()
            break