import socket
HOST = '10.0.141.90'
PORT = 8888

# UDP 
udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_client.bind('10.0.141.91', 7777)
udp_client.sendto("5555555555555555", (HOST, PORT))
udp_client.sendto("7777777777777777", (HOST, PORT))
udp_client.sendto("8888888888888888", (HOST, PORT))
udp_client.close()

# TCP
File = open("sample_file.txt")
clientMessage = File.read()
File.close()

tcp_client.bind('10.0.141.91', 7777)
tcp_client = socket.socket(socket.AF_INET, SOCK_STREAM)
tcp_client.connect((HOST, PORT))
tcp_client.sendall(clientMessage)

tcp_client.close()