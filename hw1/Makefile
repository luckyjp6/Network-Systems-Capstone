main: main.o
	g++ main.o -o main -lpcap
	sudo setcap cap_net_raw,cap_net_admin=eip main

main.o: main.cpp
	g++ -c main.cpp

report1:
	ping 10.0.141.91 -c 3

report2: client.py
	ping 10.0.141.91 -c 1
	python3 client.py