# Network Systems Capstone
Homeworks of the course Network Systems Capstone
[TOC]
## Hw1 - tcpdump
A C++ program that captures live network packets and prints some information in the packet, similar to what the tcpdump utility does.
### Implemented Arguments
- --interface {interface}, -i {interface}
- --count {number}, -c {number}  
(default = -1 -> this program will continuously capture packets until it is interrupted.)
- --filter {udp, tcp, icmp, all}, -f {udp, tcp, icmp, all}  
(default = all -> It should correctly filter out UDP, TCP, and ICMP packets.)