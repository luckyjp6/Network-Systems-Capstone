# Network Systems Capstone
Homeworks of the course Network Systems Capstone

## Hw1 - tcpdump
用C++實作類似tcpdump的功能，抓取經過特定網路卡的封包並依據封包類型印出對應資訊，支援IPv4, IPv6, ICMP, UDP, TCP等protocol。

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

## Hw2 - ARP
用C++模擬簡易的拓譜架構，並實作ARP protocol，藉由此次作業可以充分了解ARP的運作及各個host/switches處理ARP request的流程
![image](https://user-images.githubusercontent.com/96563567/225960836-88101399-192a-46d6-9dc5-fa6bd4de136f.png)

### Command
#### ping
```
h1 ping h2 (No need to print anything)
```
#### show_table 
印出arp table。
show_table (for switches and hosts)
show_table {host-name/switch-name}
```
show_table h1 (show arp table in h1)
show_table s1 (show mac table in s1)
show_table {all_hosts/all_switches}
show_table all_hosts (show all hosts’ arp table)
show_table all_switches (show all switches’ arp table)
```
#### clear
清除arp table。
```
clear h1 (clear arp table in h1)
clear s1 (clear mac table in s1)
clear all_hosts (clear all hosts' arp table
```
#### Invalid command
輸入除了上述三種command以外的command或是command格是錯誤，輸出“a wrong command”。

### Demo
![image](https://user-images.githubusercontent.com/96563567/225963628-07993ac7-c6e8-410e-8e14-a54583d48550.png)

