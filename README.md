# Network Systems Capstone
Homeworks of the course Network Systems Capstone

## Hw1 - tcpdump
A C++ program that captures live network packets and prints some information in the packet, similar to what the tcpdump utility does.

### Implemented Arguments
- --interface {interface}, -i {interface}
- --count {number}, -c {number}  
(default = -1 -> this program will continuously capture packets until it is interrupted.)
- --filter {udp, tcp, icmp, all}, -f {udp, tcp, icmp, all}  
(default = all -> It should correctly filter out UDP, TCP, and ICMP packets.)
- --port {src or dst port number}, -p {port number}

### Demo
- ICMP & UDP  
  ![image](https://user-images.githubusercontent.com/96563567/225572419-c20dbe1f-6366-4fbc-8513-1b0589bb5029.png)  
- TCP  
  Including SYN, SYN+ACK, payload*2 and ACK  
  ![image](https://user-images.githubusercontent.com/96563567/225572861-b1e716f0-631e-4680-817e-1c261433c49f.png)  

***
