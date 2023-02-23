main: main.o
	g++ main.o -o main -lpcap
	sudo setcap cap_net_raw,cap_net_admin=eip main

main.o: main.cpp
	g++ -c main.cpp

test: test.cpp
	g++ test.cpp -o test

server: 
	python3 server.py
client:
	python3 client.py