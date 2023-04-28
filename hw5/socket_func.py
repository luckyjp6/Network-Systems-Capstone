import socket
import time
import threading
import frame_struct as fr
import recv_structure as rs

time_to_stop = False
send_window = 1000
send_amount = 10
send_timeout = 0
# to_addr = ""
# self_addr = ""

reply_lock = threading.Lock()
reply_queue = list()
send_lock = threading.Lock()
send_idx = list()
wait_to_send = dict()
recv_lock = threading.Lock()
recv_streams = dict()
recv_pn = rs.recv_pn()
pn_to_stream = dict()

def get_packet(s:socket.socket, need_addr=False) -> fr.QUIC_packet:
    packet = ""
    cli_addr = ""
    try:
        if need_addr: packet, cli_addr = s.recvfrom(2000)
        else: packet = s.recv(2000)
        # print("get packet: {}".format(packet))
    except:
        return None

    if len(packet) == 0: return None

    packet = str(packet, encoding='utf-8')
    if need_addr: return fr.QUIC_packet(packet), cli_addr
    else: return fr.QUIC_packet(packet)

def send_packet(s:socket.socket, to_addr, pn, types, payload) -> None:
    packet = fr.QUIC_packet()
    packet.set(pn, types, payload)
    try:
        # print("send {}->{}".format(s.getsockname(), to_addr))
        s.sendto(packet.to_string().encode(), to_addr)
    except:
        print("broken pipe")
        exit()
    return

def add_send_queue(pn, stream_id, data):
    global wait_to_send, send_lock, send_idx, pn_to_stream

    num_segment = int(len(data)/fr.Max_payload)+1
    last = len(data) - (num_segment-1)*fr.Max_payload
    offset = 0
    
    stream_data = dict()
    for i in range(num_segment):
        fin = int(i == num_segment-1)
        length = last if fin else fr.Max_payload
        stream_payload = fr.STREAM_frame()
        stream_payload.set(stream_id, length, fin, offset, data[offset:offset+length])
        offset += fr.Max_payload
        stream_data[pn] = stream_payload.to_string()
        pn_to_stream[pn] = stream_id
        pn += 1

    send_lock.acquire()
    wait_to_send[stream_id] = stream_data
    send_idx.append(stream_id)
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

def send_loop(s:socket.socket, to_addr):
    global wait_to_send, send_lock, send_window, reply_queue, reply_lock, send_amount, pn_to_stream

    now_at = 0
    reply_lock.acquire()
    reply_lock.release()
    while True:
        # wait data
        while (not send_idx) and (not reply_queue): continue
        # print(wait_to_send)
        if wait_to_send:
            num_send = 0 # for congestion control

            window_max = min(send_window, len(send_idx)-1) # send window
            send_amount_max = min(send_amount, len(send_idx)-1) # maximum number of packet sent one time

            num_send += send_amount_max
            send_lock.acquire()
            # send every thing
            for i in range(send_amount_max):
                if now_at >= window_max: now_at = 0 # max stream num
                stream_id = send_idx[now_at]

                if stream_id == -1: # termination
                    s.close()
                    exit()

                for pn, frame in wait_to_send[stream_id].items():
                    send_packet(s, to_addr, pn, "stream", frame)
                
                now_at += 1; 
            send_lock.release()
        
        for i in range(50):
            if len(reply_queue) > 0: break
            time.sleep(0.0001)

        # send ack is prioritized
        if len(reply_queue) > 0:
            # print(reply_queue)
            reply_lock.acquire()
            for item in reply_queue:
                if len(item) == 0: continue
                send_packet(s, to_addr, 0, "ack", item)
            reply_lock.release()
            reply_queue.clear()
            continue

def recv_loop(s:socket.socket):
    global time_to_stop, recv_pn, in_recv#, send_timeout
    num_recv = 0
    # get_ack = False
    while True:
        if time_to_stop:
            for i in range(10): send_ack(s)
            in_recv = True
            exit()
        packet = get_packet(s)
        if packet == None:
            
            # if num_recv <= 0: continue
            # if not get_ack: send_timeout += 1
            # else: send_timeout = 10
            send_ack(s); # send_max_data(s, to_addr, recv_pn.lower_bound+num_recv)
        elif packet.types == "stream":
            num_recv += 1
            # record pn, don't record already receive pn
            if recv_pn.add(packet.pn): 
                # record packet
                record_stream_data(packet.payload.stream_id, packet.payload.offset, packet.payload.fin, packet.payload.payload)

        elif packet.types == "ack":
            global send_lock, wait_to_send, send_idx
            # get_ack = True
            acks = packet.payload.ack_range
            send_lock.acquire()
            for ack in acks:
                for idx in range(ack[0], ack[1]):
                    if idx in send_idx: 
                        print("pop", idx)
                        # print("send idx", id, send_idx)
                        stream_id = pn_to_stream[idx]
                        pn_to_stream.pop(idx)
                        if idx in wait_to_send[stream_id]: wait_to_send[stream_id].pop(idx)
                        if not wait_to_send[stream_id]: 
                            wait_to_send.pop(stream_id)
                            send_idx.remove(stream_id)
            send_lock.release()
        if num_recv >= 10: 
            send_ack(s)
            num_recv = 0
        # elif packet.types == "max_data":
        #     global send_window
        #     send_window = packet.payload.max_len
    """
    congestion control
    """

def send_ack(s:socket.socket):
    global recv_pn, reply_queue, reply_lock
    # send ack
    ack_packet = fr.ACK_frame()
    acks = recv_pn.get_needed()
    if acks == None: return
    
    ack_packet.set(acks)

    reply_lock.acquire()
    reply_queue.append(ack_packet.to_string())
    reply_lock.release()
    # print(reply_queue)
    # send_packet(s, to_addr, 0, "ack", ack_packet.to_string())
    return
def send_max_data(s:socket.socket, to_addr, add:int):
    global reply_queue, reply_lock
    payload = fr.MAX_DATA_frame(str(add))
    reply_lock.acquire()
    reply_queue.append(("max_data", payload.to_string()))
    reply_lock.release()
    # send_packet(s, to_addr, 0, "max_data", payload.to_string())
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

def start_thread(to_addr, recv_socket):
    recv_socket.settimeout(0.01)
    send_thread = threading.Thread(target=send_loop, args=[recv_socket, to_addr])
    send_thread.start()
    recv_thread = threading.Thread(target=recv_loop, args=[recv_socket])
    recv_thread.start()

def safe_close(s:socket.socket):
    global time_to_stop, wait_to_send, send_idx, reply_queue, reply_lock, in_recv
    
    # wait until all packets sent
    while wait_to_send: continue

    # last ack   
    # print("wait entering recv_loop")
    # enshure entering recv_loop
    in_recv = False 
    while not in_recv: time_to_stop = True

    # stop
    send_lock.acquire()
    wait_to_send[-1] = "no"
    send_idx.append(-1)
    send_lock.release()
    # print("wait send exit")
    while threading.active_count() > 1: continue