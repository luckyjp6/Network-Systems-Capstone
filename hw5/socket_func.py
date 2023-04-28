import socket
import time
import threading
import frame_struct as fr
import recv_structure as rs

time_to_stop = False
send_window = 1000
# to_addr = ""
# self_addr = ""

reply_lock = threading.Lock()
reply_queue = list()
send_lock = threading.Lock()
wait_to_send = dict()
recv_lock = threading.Lock()
recv_streams = dict()
recv_pn = rs.recv_pn()

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
        # print("send {}->{}: {}".format(s.getsockname(), to_addr, packet.to_string()))
        s.sendto(packet.to_string().encode(), to_addr)
    except:
        print("broken pipe")
        exit()
    return

def add_send_queue(pn, stream_id, data):
    global wait_to_send, send_lock

    num_segment = int(len(data)/fr.Max_payload)+1
    last = len(data) - (num_segment-1)*fr.Max_payload
    offset = 0

    send_lock.acquire()
    for i in range(num_segment):
        fin = int(i == num_segment-1)
        length = last if fin else fr.Max_payload
        stream_payload = fr.STREAM_frame()
        stream_payload.set(stream_id, length, fin, offset, data[offset:offset+length])
        offset += fr.Max_payload
        wait_to_send[pn] = stream_payload.to_string()
        pn += 1
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
    global wait_to_send, send_lock, send_window, reply_queue, reply_lock

    now_at = 0
    to_limit = False
    while True:
        # wait if empty
        while (not wait_to_send) and (len(reply_queue) == 0): continue

        if len(reply_queue) > 0:
            reply_lock.acquire()
            for item in reply_queue:
                send_packet(s, to_addr, 0, item[0], item[1])
            reply_lock.release()
            reply_queue.clear()
            continue

        if not to_limit: now_at = 0
        num_send = 0
        to_limit = False

        send_lock.acquire()
        # send every thing
        for pn, frame in wait_to_send.items(): # pn: STREAM_frame.to_string()
            if pn == -1: 
                s.close()
                exit()
            if pn >= now_at: 
                send_packet(s, to_addr, pn, "stream", frame)
                num_send += 1
                send_window -= 1
                now_at = pn
                if send_window <= 0: 
                    to_limit = True
                    break
        send_lock.release()

        time.sleep(0.5)

def recv_loop(s:socket.socket, to_addr):
    global time_to_stop, recv_pn, in_recv
    num_recv = 0
    while True:
        packet = get_packet(s)
        if packet == None:
            if time_to_stop: 
                send_ack(s, to_addr)
                in_recv = True
                exit()
            if num_recv <= 0: continue

            send_ack(s, to_addr); send_max_data(s, to_addr, num_recv)
            num_recv = 0
        elif packet.types == "stream":
            num_recv += 1
            # record packet
            record_stream_data(packet.payload.stream_id, packet.payload.offset, packet.payload.fin, packet.payload.payload)
            # record pn
            recv_pn.add(packet.pn)
        elif packet.types == "ack":
            global send_lock
            acks = packet.payload.ack_range
            send_lock.acquire()
            for ack in acks:
                for id in range(ack[0], ack[1]):
                    if id in wait_to_send: wait_to_send.pop(id)
            send_lock.release()
        elif packet.types == "max_data":
            global send_window
            send_window = packet.payload.max_len
    """
    congestion control
    """

def send_ack(s:socket.socket, to_addr):
    global recv_pn, reply_queue, reply_lock
    # send ack
    ack_packet = fr.ACK_frame()
    acks = recv_pn.get_needed()
    if len(acks) == 0: return
    ack_packet.set(acks)

    reply_lock.acquire()
    reply_queue.append(("ack", ack_packet.to_string()))
    reply_lock.release()
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
    recv_thread = threading.Thread(target=recv_loop, args=[recv_socket, to_addr])
    recv_thread.start()

def safe_close(s:socket.socket):
    global time_to_stop, wait_to_send, reply_queue, in_recv
    
    # wait until all packets sent
    while wait_to_send: continue

    # last ack
    in_recv = False    
    # print("wait entering recv_loop")
    # enshure entering recv_loop
    while not in_recv: time_to_stop = True
    # print("wait reply sent")
    # wait send_loop handle reply
    while len(reply_queue) > 0: continue
    # print("stop")
    # stop
    send_lock.acquire()
    wait_to_send[-1] = "no"
    send_lock.release()
    while threading.active_count() > 1: continue