import threading, json, socket
from os import path
from misc import sha1_chunks
from enum import Enum

class packet_type(Enum):
    FILE_HEADER = 1
    TRANSFER_REJECT = 2
    TRANSFER_ACCEPT = 3
    TRANSFER_PAUSED = 4
    TRANSFER_RESUMED = 5
    TRANSFER_CANCELLED = 6
    TRANSFER_FINISHED = 7

active_inbound_transfers = {}
active_outbound_transfers = {}

def listen_for_info(info_receiver_socket, queue):
    info_receiver_socket.listen()
    while True:
        other_socket, addr = info_receiver_socket.accept()
        threading.Thread(target=process_info, args=(other_socket, addr, queue)).start()

def process_info(socket, addr, queue):
    packet_length = int.from_bytes(socket.recv(4), byteorder='big')
    packet = socket.recv(packet_length).decode("utf-8")

    if not packet: return
    info = json.loads(packet)
    info["type"] = packet_type(info["type"])

    if info["type"] == packet_type.FILE_HEADER:
        queue.put((info, socket))
    if info["type"] == packet_type.TRANSFER_PAUSED:
        queue.put((info, socket))
        active_inbound_transfers[info[addr[0]]][info["reference_hash"]]["control_flag"] = packet_type.TRANSFER_PAUSED

    if info["type"] == packet_type.TRANSFER_RESUMED:
        active_inbound_transfers[info[addr[0]]][info["reference_hash"]]["control_flag"] = packet_type.TRANSFER_RESUMED
        active_inbound_transfers[info[addr[0]]][info["reference_hash"]]["pausing_condition"].notify()

    if info["type"] == packet_type.TRANSFER_CANCELLED:
        queue.put((info, socket))
        active_inbound_transfers[info[addr[0]]][info["reference_hash"]]["control_flag"] = packet_type.TRANSFER_CANCELLED

def listen_for_transfer(file_receiver_socket, queue):
    file_receiver_socket.listen()
    while True:
        other_socket, addr = file_receiver_socket.accept()
        ip = addr[0]
        if not ip in active_inbound_transfers:
            other_socket.close()
        threading.Thread(target=process_transfer, args=(other_socket, ip, queue)).start()

def process_transfer(socket, ip, queue):
    reference_hash = list(active_inbound_transfers[ip].keys())[-1]
    with open(active_inbound_transfers[ip][reference_hash]["save_path"], 'wb') as file:
        while True:
            chunk = socket.recv(8192)
            if not chunk:
                break
            file.write(chunk)
    # send a confirmation and or check hash

    queue.put(({"type": packet_type.TRANSFER_FINISHED, "ip": ip, "reference_hash": reference_hash, "receiving": True}, None))
    del active_inbound_transfers[ip][reference_hash]
    if not active_inbound_transfers[ip]:
        del active_inbound_transfers[ip]

def create_file_info_header(file_path):
    file_name = path.basename(file_path)
    file_size = path.getsize(file_path)
    file_hash = sha1_chunks(file_path)

    data = {
        "type": packet_type.FILE_HEADER.value,
        "file_name": file_name,
        "file_size": file_size,
        "sha1": file_hash
    }

    header = json.dumps(data).encode("utf-8")
    return header

def transfer_file(sender_socket, ip, file_path, reference_hash, queue):
    
    sender_socket.connect((ip, 15555))

    with open(file_path, 'rb') as file:
        while chunk := file.read(8192):
            if ip in active_outbound_transfers:        
                if active_outbound_transfers[ip][reference_hash]["control_flag"] == packet_type.TRANSFER_CANCELLED:
                    break
                
                if active_outbound_transfers[ip][reference_hash]["control_flag"] == packet_type.TRANSFER_PAUSED:

                    with active_outbound_transfers[ip][reference_hash]["pausing_condition"]:
                        active_outbound_transfers[ip][reference_hash]["pausing_condition"].wait()

            sender_socket.send(chunk)

    if active_outbound_transfers[ip][reference_hash]["control_flag"] == packet_type.TRANSFER_CANCELLED:  
        del active_outbound_transfers[ip][reference_hash]
        if not active_outbound_transfers[ip]:
            del active_outbound_transfers[ip]
    else:
        sender_socket.close()

    queue.put(({"type": packet_type.TRANSFER_FINISHED, "ip": ip, "reference_hash": reference_hash, "receiving": False}, None))


def initiate_transfer(ip, file_path, queue):
    def transfer_thread():
        sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        response = send_transfer_request(sender_socket, ip, file_path)
        sender_socket.close()
        if response["type"] == packet_type.TRANSFER_REJECT:
            queue.put(({"type": packet_type.TRANSFER_REJECT, "ip":ip}, None))
        else:
            sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            file_name = path.basename(file_path)
            file_size = path.getsize(file_path)
            reference_hash = sha1_chunks(file_path)
            add_to_active_outbound_transfers(ip, file_name, file_size, reference_hash, file_path)

            info = {
                "type": packet_type.TRANSFER_ACCEPT,
                "ip":ip,
                "reference_hash": reference_hash
            }

            queue.put((info, None))

            transfer_file(sender_socket, ip, file_path, reference_hash, queue)

    threading.Thread(target=transfer_thread).start()


def send_transfer_request(sender_socket, ip, file_path):
    header = create_file_info_header(file_path)
    
    sender_socket.connect((ip, 15556))
    sender_socket.send(len(header).to_bytes(4, byteorder='big'))
    sender_socket.send(header)
    
    packet_length = int.from_bytes(sender_socket.recv(4), byteorder='big')
    packet = sender_socket.recv(packet_length).decode("utf-8")

    info = json.loads(packet)
    info["type"] = packet_type(info["type"])
    return info

def send_response(response_type, socket):
    response = {
        "type": response_type.value
    }

    response = json.dumps(response).encode("utf-8")
    socket.send(len(response).to_bytes(4, byteorder='big'))
    socket.send(response)

def toggle_transfer_pause(ip, reference_hash, from_sending_peer):
    response = None;
    dict = None
    if from_sending_peer:
        dict = active_outbound_transfers
    else:
        dict = active_inbound_transfers

    value = dict[ip][reference_hash]["control_flag"]

    if value == packet_type.TRANSFER_ACCEPT or value == packet_type.TRANSFER_RESUMED:
        dict[ip][reference_hash]["control_flag"] = packet_type.TRANSFER_PAUSED
    else:
        dict[ip][reference_hash]["control_flag"] = packet_type.TRANSFER_RESUMED
        dict[ip][reference_hash]["pausing_condition"].notify()
    

    response = {
        "type": dict[ip][reference_hash]["control_flag"].value,
        "reference_hash": reference_hash
    }

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, 15556))
    response = json.dumps(response).encode("utf-8")
    s.send(len(response).to_bytes(4, byteorder='big'))
    s.send(response)
    s.close()

def add_to_active_inbound_transfers(ip, file_name, file_size, hash, save_path):
    if not ip in active_inbound_transfers:
        active_inbound_transfers[ip] = {}
    
    active_inbound_transfers[ip][hash] = {
        "file_name": file_name,
        "file_size": file_size,
        "save_path": save_path,
        "control_flag": packet_type.TRANSFER_ACCEPT,
        "pausing_condition": threading.Condition()
    } 

def add_to_active_outbound_transfers(ip, file_name, file_size, hash, file_path):
    if not ip in active_outbound_transfers:
        active_outbound_transfers[ip] = {}
    
    active_outbound_transfers[ip][hash] = {
        "file_name": file_name,
        "file_size": file_size,
        "file_path": file_path,
        "control_flag": packet_type.TRANSFER_ACCEPT,
        "pausing_condition": threading.Condition()
    } 

def initialise_receiver_sockets(queue):
    file_receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    file_receiver_socket.setblocking(True)
    file_receiver_socket.bind(("0.0.0.0", 15555))

    info_receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    info_receiver_socket.setblocking(True)
    info_receiver_socket.bind(("0.0.0.0", 15556))

    threading.Thread(target=listen_for_info, args=(info_receiver_socket, queue), daemon=True).start()
    threading.Thread(target=listen_for_transfer, args=(file_receiver_socket, queue), daemon=True).start()