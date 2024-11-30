import threading, json, socket
from os import path
from misc import sha1_chunks
from enum import Enum
import queue

class packet_type(Enum):
    FILE_HEADER = 1
    TRANSFER_REJECT = 2
    TRANSFER_ACCEPT = 3
    TRANSFER_PAUSED = 4
    TRANSFER_CANCELLED = 5


processed_info_queue = queue.Queue()

def listen_for_info(info_receiver_socket, queue):
    info_receiver_socket.listen()
    while True:
        other_socket, addr = info_receiver_socket.accept()
        threading.Thread(target=receive_info, args=(other_socket, addr, queue)).start()


def receive_info(socket, addr, queue):
    packet_length = int.from_bytes(socket.recv(4), byteorder='big')
    packet = socket.recv(packet_length).decode("utf-8")

    info = json.loads(packet)
    info["type"] = packet_type(info["type"])
    queue.put((info, addr, socket))


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

def transfer_file(ip, file_path):
    def transfer_thread():
        sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        response = send_transfer_request(sender_socket, ip, file_path)
        if response["type"] == packet_type.TRANSFER_REJECT:
            print("Transfer rejected")
        else:
            print("Transfer accepted")


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



def initialise_receiver_sockets(queue):
    file_receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    file_receiver_socket.setblocking(True)
    file_receiver_socket.bind(("0.0.0.0", 15555))

    info_receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    info_receiver_socket.setblocking(True)
    info_receiver_socket.bind(("0.0.0.0", 15556))

    threading.Thread(target=listen_for_info, args=(info_receiver_socket, queue), daemon=True).start()
    # threading.Thread(target=listen_for_transfer, args=(file_receiver_socket,), daemon=True)