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

***

## Hw3 - Aloha, Slotted Aloha, CSMA, and CSMA/CD
用python模擬並分析不同情況下Aloha, Alotted Aloha, CSMA和CSMA/CD的channel efficiency。

### Analysis
- 不同數量的host對channel efficiency的影響![image](https://github.com/luckyjp6/Network-Systems-Capstone/assets/96563567/a5fc8935-1c9c-49c6-809d-97623e7d594f)
- 調整重新發送封包的最大等待時間(max_colision_wait_time)和Slotted Aloha重送封包的機率(p_resend)對channel efficiency的影響，使整體曲線更加平滑![image](https://github.com/luckyjp6/Network-Systems-Capstone/assets/96563567/1268b30c-4c14-4476-bf91-52046a6a50fa)

***

## Hw4 - RIP & OSPF
以python分別實作OSPF和RIP。

### Implementation
- OSPF: 實作一個class處理各個node的行為。self.origin_links儲存最一開始的links cost，即實際連線情形，flood時依據self.origin_links判斷對應node之間是否有實體連線，若有就傳送該node上一輪新拿到的的link table。![image](https://github.com/luckyjp6/Network-Systems-Capstone/assets/96563567/d2cba9d9-9f5f-49c9-b440-77d3ebaf30ab)
- RIP: 和OSPF使用同樣架構，但只傳送自己的links（即distance vector）。![image](https://github.com/luckyjp6/Network-Systems-Capstone/assets/96563567/407e29dc-74f5-4d3b-b7cd-03c362f82a38)

***

## Hw5 - QUIC
以python實作QUIC server和client。

## 細節待補

***

## Hw6 - HTTP
以python實作HTTP1.0, HTTP1.1, HTTP2.0和HTTP3.0的server和client。

## 細節待補

*** 

## Hw7 - SDN
以python撰寫SDN架構中的topology和controller部分，依據spec要求，在match到特定packet條件時forward packet、drop packet或參考特定table進行處理。

## 細節待補
