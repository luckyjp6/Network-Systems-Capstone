# Network Systems Capstone
Homeworks of the course Network Systems Capstone
[Toc]
## Hw1 - tcpdump
A C++ program that captures live network packets and prints some information in the packet, similar to what the tcpdump utility does.
### Implemented Arguments
- --interface {interface}, -i {interface}
- --count {number}, -c {number}  
(default = -1 -> this program will continuously capture packets until it is interrupted.)
- --filter {udp, tcp, icmp, all}, -f {udp, tcp, icmp, all}  
(default = all -> It should correctly filter out UDP, TCP, and ICMP packets.)
![image](https://user-images.githubusercontent.com/96563567/220227724-ca3d2146-db6d-42e8-9e86-ebd14d23eef4.png)
