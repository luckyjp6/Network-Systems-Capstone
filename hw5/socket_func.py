import socket
import time
import threading
import frame_struct as fr
import recv_structure as rs
import math

time_to_stop = False
send_window = 10
send_amount = 10
num_ack = 0
num_send = 0
to_addr = ""
max_pn = 100
max_recv = 0
no_ack_count = 0

reply_lock = threading.Lock()
reply_queue = list()
send_lock = threading.Lock()
wait_to_send = dict()
pn_to_send = dict()
recv_lock = threading.Lock()
recv_streams = dict()
recv_pn = rs.recv_pn()
stream_remain = dict()

def get_packet(s:socket.socket, need_addr=False) -> fr.QUIC_packet:
    packet = ""
    cli_addr = ""
    try:
        if need_addr: packet, cli_addr = s.recvfrom(50000)
        else: packet = s.recv(50000)
        # if fr.QUIC_packet(str(packet, encoding='utf-8')).types == "ack": print("get packet: {}".format(packet))
        # else: print(packet)
    except socket.timeout:
        return None
    except (ConnectionResetError, BrokenPipeError):
        print("get packet, broken pipe")
        exit()

    if len(packet) == 0: return None

    packet = str(packet, encoding='utf-8')
    if need_addr: return fr.QUIC_packet(packet), cli_addr
    else: return fr.QUIC_packet(packet)

def send_packet(s:socket.socket, pn, types, payload) -> None:
    global to_addr
    packet = fr.QUIC_packet()
    packet.set(pn, types, payload)
    try:
        # if types == "ack": print("send: {}".format(packet.to_string()))
        # else: print("send: {}".format(packet.pn))
        s.sendto(packet.to_string().encode(), to_addr)
    except:
        print("broken pipe")
        exit()
    return

def add_send_queue(pn, stream_id, data):
    global wait_to_send, send_lock

    num_segment = math.ceil(len(data)/fr.Max_payload)
    last = len(data) - (num_segment-1)*fr.Max_payload
    offset = 0
    
    stream_dict = dict()
    for i in range(num_segment):
        fin = int(i == num_segment-1)
        length = last if fin else fr.Max_payload
        stream_payload = fr.STREAM_frame()
        stream_payload.set(stream_id, length, fin, offset, data[offset:offset+length])
        offset += fr.Max_payload
        stream_dict[i] = stream_payload.to_string()
    send_lock.acquire()
    wait_to_send[stream_id] = stream_dict
    send_lock.release()

    return pn
def check_done():
    global recv_streams, recv_lock

    recv_lock.acquire()
    for id, item in recv_streams.items():
        if item.is_done(): 
            recv_lock.release()
            return id
    recv_lock.release()

    return -1

def send_loop(s:socket.socket):
    global wait_to_send, send_lock, reply_queue, send_amount, num_ack, num_send

    # num_send = 0 # for congestion control
    # now_at = 0
    pn = 0
    while True:
        # wait data
        while (not wait_to_send):continue # and (not reply_queue): continue
        # print("wait to send num", len(wait_to_send))
        num_send = 0
        send_lock.acquire()
        if wait_to_send:            
            global send_window, pn_to_send, max_pn
            tmp = dict()
            for key, value in pn_to_send.items():
                if key < pn - send_amount*50: continue
                else: tmp[key] = value
            pn_to_send = tmp
            window_max = min(send_window, len(wait_to_send)) # stream/send

            start_pn = pn
            # send every thing
            for stream_id, data in wait_to_send.items():
                # termination
                if stream_id == -1 and len(data) == 0: send_lock.release(); exit()
                
                if window_max <= 0: break
                
                send_amount_max = min(send_amount, len(data)) # packet/send
                for idx, freg in data.items():
                    # flow control
                    if pn > max_pn: break
                    if stream_id in stream_remain:
                        if stream_remain[stream_id] <= 0: break
                    # avoid Head-of-Line
                    if send_amount_max <= 0: break
                    
                    send_packet(s, pn, "stream", freg)
                    pn_to_send[pn] = (stream_id, idx)
                    pn += 1
                    send_amount_max -= 1
                window_max -= 1
            num_send = pn - start_pn
        send_lock.release()

        # wait ack
        global max_recv
        for i in range(100):
            if max_recv >= pn-num_send: break
            time.sleep(0.001)

        send_lock.acquire()
        if num_send > 0: 
            send_rate = num_ack/num_send
            # print(send_rate)
            if (send_rate < 0.7) and (send_amount >= 2): send_amount = int(send_amount / 2)
            elif send_amount < 100: send_amount += 3
            num_ack = 0
            num_send = 0
        send_lock.release()


def recv_loop(s:socket.socket):
    global time_to_stop, send_amount, send_window
    
    num_recv = 0
    while True:
        if time_to_stop: exit()
        packet = get_packet(s)
        if (packet == None) or (num_recv >= send_amount*send_window): 
            # print(num_recv, send_amount*send_window)
            send_ack(s)
            num_recv = 0
        elif packet.types == "stream":
            global recv_pn
            num_recv += 1
            # record pn, don't record already receive pn
            recv_pn.add(packet.pn)
            # record packet
            record_stream_data(packet.payload.stream_id, packet.payload.offset, packet.payload.fin, packet.payload.payload)

        elif packet.types == "ack":
            global send_lock, wait_to_send, num_ack, pn_to_send, max_pn, max_recv
            # while num_ack != 0: continue
            num_ack = packet.payload.total_num
            acks = packet.payload.ack_range
            max_pn = packet.payload.max_pn
            stream_remain = packet.payload.stream_remain
            
            send_lock.acquire()            
            # print(pn_to_send)
            # print(acks)
            for ack in acks:
                for pn in range(ack[0], ack[1]):
                    if pn not in pn_to_send: continue
                    i, j = pn_to_send[pn]
                    max_recv = max(max_recv, i, j)
                    if i in wait_to_send and j in wait_to_send[i]: 
                        del wait_to_send[i][j]
                        if not wait_to_send[i]: del wait_to_send[i]
                    pn_to_send.pop(pn)
                
            send_lock.release()

def send_ack(s:socket.socket):
    global recv_pn, send_lock, recv_streams, no_ack_count
    
    remain_size = 10000010
    per_stream_remain_size = dict()
    
    # get remain size
    for id, stream in recv_streams.items():
        stream_size = stream.get_size()
        per_stream_remain_size[id] = 1000000 - stream_size
        remain_size -= stream_size
    if remain_size < 0: remain_size = 0
    pn_add = int(remain_size/fr.Max_payload)

    # get acks
    total_num, max_pn, acks = recv_pn.get_needed()

    # set packet
    ack_packet = fr.ACK_frame()
    if total_num == 0: 
        no_ack_count += 1
        if no_ack_count < 50: return
        no_ack_count = 0

    ack_packet.set(total_num, max_pn + pn_add, per_stream_remain_size, acks)
    
    # send ack
    send_lock.acquire()
    send_packet(s, 0, "ack", ack_packet.to_string())
    send_lock.release()
    return


def record_stream_data(stream_id, offset, fin, payload):
    global recv_streams, recv_lock

    recv_lock.acquire()
    # first-time recv
    if stream_id not in recv_streams:
        recv_streams[stream_id] = rs.recv_data()
    
    # append data
    recv_streams[stream_id].add(offset, fin, payload)
    recv_lock.release()  

    return

def start_thread(t_addr, recv_socket):
    global to_addr
    to_addr = t_addr
    recv_socket.settimeout(0.05)
    send_thread = threading.Thread(target=send_loop, args=[recv_socket])
    send_thread.start()
    recv_thread = threading.Thread(target=recv_loop, args=[recv_socket])
    recv_thread.start()

def safe_close(s:socket.socket):
    global time_to_stop, wait_to_send, reply_queue, reply_lock
    
    # print("wait data")
    # wait until all packets sent
    while wait_to_send: 
        # print(pn_to_send)
        # print(wait_to_send)
        continue
    send_lock.acquire()
    wait_to_send[-1] = ""
    send_lock.release()
    # acks = recv_pn.get_needed()
    # print(acks)

    time_to_stop = True
    # print("to send ack")
    for i in range(10): send_ack(s)
    # for i in range(1): 
    
    # print("stop")
    # stop
    # print("wait send exit")
    while threading.active_count() > 1: continue
    s.close()