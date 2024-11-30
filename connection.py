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

permitted_ips = {}
transfer_control_flags = {}
transfer_pausing_conditions = {}

def listen_for_info(info_receiver_socket, queue):
    info_receiver_socket.listen()
    while True:
        other_socket, _ = info_receiver_socket.accept()
        threading.Thread(target=process_info, args=(other_socket, queue)).start()

def process_info(socket, queue):
    packet_length = int.from_bytes(socket.recv(4), byteorder='big')
    packet = socket.recv(packet_length).decode("utf-8")

    if not packet: return
    info = json.loads(packet)
    info["type"] = packet_type(info["type"])

    if info["type"] == packet_type.FILE_HEADER:
        queue.put((info, socket))
    if info["type"] == packet_type.TRANSFER_PAUSED:
        # put in connections queue
        print()
    if info["type"] == packet_type.TRANSFER_CANCELLED:
        # put in connections queue
        print()

def listen_for_transfer(file_receiver_socket):
    file_receiver_socket.listen()
    while True:
        other_socket, addr = file_receiver_socket.accept()
        ip = addr[0]
        if not ip in permitted_ips:
            other_socket.close()
        threading.Thread(target=process_transfer, args=(other_socket, ip)).start()

def process_transfer(socket, ip):
    with open(permitted_ips[ip], 'wb') as file:
        while True:
            chunk = socket.recv(8192)
            if not chunk:
                break
            file.write(chunk)
    del permitted_ips[ip]

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

def transfer_file(sender_socket, ip, file_path):
    
    sender_socket.connect((ip, 15555))

    with open(file_path, 'rb') as file:
        while chunk := file.read(8192):
            if ip in transfer_control_flags:        
                if transfer_control_flags[ip] == packet_type.TRANSFER_CANCELLED:
                    del transfer_control_flags[ip]
                    break
                
                if transfer_control_flags[ip] == packet_type.TRANSFER_PAUSED:
                    transfer_pausing_conditions[ip] = threading.Condition()

                    with transfer_pausing_conditions[ip]:
                        transfer_pausing_conditions[ip].wait()
                        del transfer_control_flags[ip]

            sender_socket.send(chunk)

    if ip in transfer_control_flags:  
        if transfer_control_flags[ip] == packet_type.TRANSFER_CANCELLED:
            del transfer_control_flags[ip]
        else:
            sender_socket.close()



def initiate_transfer(ip, file_path, queue):
    def transfer_thread():
        sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        response = send_transfer_request(sender_socket, ip, file_path)
        sender_socket.close()
        if response["type"] == packet_type.TRANSFER_REJECT:
            queue.put(({"type": packet_type.TRANSFER_REJECT, "ip":ip}, None))
        else:
            sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            transfer_file(sender_socket, ip, file_path)

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


def initialise_receiver_sockets(queue):
    file_receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    file_receiver_socket.setblocking(True)
    file_receiver_socket.bind(("0.0.0.0", 15555))

    info_receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    info_receiver_socket.setblocking(True)
    info_receiver_socket.bind(("0.0.0.0", 15556))

    threading.Thread(target=listen_for_info, args=(info_receiver_socket, queue), daemon=True).start()
    threading.Thread(target=listen_for_transfer, args=(file_receiver_socket,), daemon=True).start()