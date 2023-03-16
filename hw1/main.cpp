#include <iostream>
#include <stdlib.h>
#include <pcap/pcap.h> 
#include <string.h>
#include <vector>
#include <getopt.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/udp.h>

using namespace std;

char opt_sh[] = "i:c:f:p:";
option opt_long[] = {
    {"interface", required_argument, NULL, 'i'},
    {"count", required_argument, NULL, 'c'},
    {"filter", required_argument, NULL, 'f'},
    {"port", required_argument, NULL, 'p'}
};

enum proto {ICMP, TCP, UDP};

void process_args(int argc,  char *const argv[], char* Interface, int &Count, char* Filter, int &Port) {
    // init
    Count = -1;
    Port = -1;
    memset(Interface, 0, 256);
    memset(Filter, 0, 10);

    // parse args
    int opt_index = 0;
    while (1) {
        int get = getopt_long(argc, argv, opt_sh, opt_long, &opt_index);

        if (get == -1) break;

        switch (get)
        {
        case 'i':
            strcpy(Interface, optarg);
            break;
        case 'c':
            Count = atoi(optarg);
            break;
        case 'f':
            strcpy(Filter, optarg);
            break;
        case 'p':
            Port = atoi(optarg);
            break;
        }
    }
}

int main(int argc, char* const argv[]) 
{
    pcap_if_t   *devices = NULL; 
    char        errbuf[PCAP_ERRBUF_SIZE];
    char        ntop_buf[256];
    struct ether_header *eptr;
    vector<pcap_if_t*>  vec; // vec is a vector of pointers pointing to pcap_if_t 
    
    //get all devices 
    if(-1 == pcap_findalldevs(&devices, errbuf)) {
        fprintf(stderr, "pcap_findalldevs: %s\n", errbuf); // if error, fprint error message --> errbuf
        exit(1);
    }

    //list all device
    int cnt = 0;
    for(pcap_if_t *d = devices; d ; d = d->next, cnt++)
    {
        vec.push_back(d);
        // cout<<"Name: "<<d->name<<endl;
    }
    
    int         Count, Port;
    char        Interface[256]; // pcap_if_t
    char        Filter[50];
    process_args(argc, argv, Interface, Count, Filter, Port);
    if (strlen(Interface) == 0) strcpy(Interface, vec[0]->name);
    if (strlen(Filter) == 0 || strcmp(Filter, "all") == 0) strcpy(Filter, "udp || tcp || icmp");
    
    bpf_program fp; // for filter, compiled in "pcap_compile"
    pcap_t *handle;
    handle = pcap_open_live(Interface, 65535, 1, 1, errbuf);  
    //pcap_open_live(device, snaplen, promise, to_ms, errbuf), interface is your interface, type is "char *"   
    

    if(!handle|| handle == NULL)
    {
        fprintf(stderr, "pcap_open_live(): %s\n", errbuf);
        exit(1);
    }
 
    if(-1 == pcap_compile(handle, &fp, Filter, 1, PCAP_NETMASK_UNKNOWN) ) // compile "your filter" into a filter program, type of {your_filter} is "char *"
    {
        pcap_perror(handle, "pkg_compile compile error\n");
        exit(1);
    }
    if(-1 == pcap_setfilter(handle, &fp)) { // make it work
        pcap_perror(handle, "set filter error\n");
        exit(1);
    }

    while(Count != 0) 
    {   
        pcap_pkthdr header;
        const unsigned char* packet = pcap_next(handle, &header);
        if (packet == NULL) break;
        
        // ethernet header
        packet += 14;

        char src[50], dst[50];

        // get ip version
        int version = packet[0] >> 4;
        proto pro;
        int payload_length = 0;

        switch (version) {
        case 4:
            iphdr ip_h;
            memcpy(&ip_h, packet, sizeof(iphdr));
            in_addr ip4_addr;
            memcpy(&ip4_addr, &ip_h.saddr, 4);
            if (inet_ntop(AF_INET, &ip4_addr, src, INET6_ADDRSTRLEN) == NULL) {
                perror("inet ntop");
                exit(-1);
            }
            memcpy(&ip4_addr, &ip_h.daddr, 4);
            if (inet_ntop(AF_INET, &ip4_addr, dst, INET6_ADDRSTRLEN) == NULL) {
                perror("inet ntop");
                exit(-1);
            }

            // get protocol
            if (ip_h.protocol == 6) pro = TCP;
            else if (ip_h.protocol == 17) pro = UDP;
            else if (ip_h.protocol == 1) pro = ICMP;
            // get payload length
            payload_length = ntohs((int)ip_h.tot_len) - (ip_h.ihl << 2);

            packet += (ip_h.ihl << 2);
            break;
        case 6:
            in6_addr ip6_ddr;
            memcpy(&ip6_ddr, packet+8, 16);
            if (inet_ntop(AF_INET6, &ip6_ddr, src, INET6_ADDRSTRLEN) == NULL) {
                perror("inet ntop");
                exit(-1);
            }
            memcpy(&ip6_ddr, packet+8+16, 16);
            if (inet_ntop(AF_INET6, &ip6_ddr, dst, INET6_ADDRSTRLEN) == NULL) {
                perror("inet ntop");
                exit(-1);
            }
            // get payload length
            payload_length = (packet[4] << 4) + packet[5];
            int nxt = packet[6];
            packet += 40; // IPv6 header length
            while (1) {
                // fragment 
                if (nxt == 51) packet += 8;
                else packet += packet[1];
                

                // get protocol
                if (nxt == 6) pro = TCP;
                else if (nxt == 17) pro = UDP;
                else if (nxt == 58) pro = ICMP;
                else {
                    nxt = packet[0];
                    continue;
                }
                break;
            }
            break;
        }

        if (pro == ICMP) {
            printf("Transport type: ICMP\n");
            printf("Source IP: %s\n", src);
            printf("Destination IP: %s\n", dst);
            printf("ICMP type value: %d\n", (int)packet[0]);
        }else {
            int src_port, dst_port, tmp;
            memcpy(&tmp, packet, 2);
            src_port = ntohs(tmp);
            memcpy(&tmp, packet+2, 2);
            dst_port = ntohs(tmp);
            if (!(Port == -1 || Port == src_port || Port == dst_port)) continue;

            if (pro == TCP) {
                printf("Transport type: TCP\n");
                printf("Source IP: %s\n", src);
                printf("Destination IP: %s\n", dst);
                printf("Source port: %d\n", src_port);
                printf("Destination port: %d\n", dst_port);

                tcphdr hdr;
                memcpy(&hdr, packet, sizeof(tcphdr));
                int hdr_len = hdr.doff << 2;

                payload_length -= hdr_len;
                packet += hdr_len;

                printf("Payload:");
                if (payload_length > 0) 
                    for (int i = 0; i < min(16, (int)payload_length); i++) 
                        printf(" %X", (int)packet[i]);
                printf("\n");
            } else if (pro == UDP) {
                printf("Transport type: UDP\n");
                printf("Source IP: %s\n", src);
                printf("Destination IP: %s\n", dst);
                printf("Source port: %d\n", src_port);
                printf("Destination port: %d\n", dst_port);
                payload_length -= 8;

                packet += 8;
                printf("Payload:");
                if (payload_length > 0) 
                    for (int i = 0; i < min(16, (int)payload_length); i++) 
                        printf(" %X", (int)packet[i]);
                printf("\n");
            }
        }
        if (Count != -1) Count --;
        printf("\n");
    }

    pcap_freealldevs(devices);

    return 0;
    
}