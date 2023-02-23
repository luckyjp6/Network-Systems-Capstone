import socket
HOST = '10.0.141.91'
PORT = 8888

# UDP 
udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_client.bind(('10.0.141.90', 7777))
msg = '5555555555555555'
udp_client.sendto(msg.encode(), (HOST, PORT))
msg = '7777777777777777'
udp_client.sendto(msg.encode(), (HOST, PORT))
msg = '8888888888888888'
udp_client.sendto(msg.encode(), (HOST, PORT))
udp_client.close()

# TCP
File = open("sample_file.txt")
clientMessage = File.read()
File.close()

tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_client.bind(('10.0.141.90', 7777))
tcp_client.connect((HOST, PORT))
tcp_client.sendall(clientMessage.encode())

tcp_client.close()