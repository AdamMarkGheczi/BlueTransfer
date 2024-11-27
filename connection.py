import os
import socket
from struct import pack, unpack

file_sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

file_receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
file_receiver_socket.setblocking(False)
file_receiver_socket.bind(("0.0.0.0", 15555))

info_sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

info_receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
info_receiver_socket.setblocking(True)
info_receiver_socket.bind(("0.0.0.0", 15556))
info_receiver_socket.listen()


def create_file_info_header(fileName, fileSize):
    fileName_bytes = fileName.encode('utf-8')
    fileName_length = len(fileName_bytes)

    header = pack(f"!H{fileName_length}sQ", fileName_length, fileName_bytes, fileSize)

    return header


# file_sender_socket.connect(remoteAddr)
# file = open(file_path, "rb")

def ReceiveFileInfoHeader(receiver_socket):
    other_socket, addr = receiver_socket.accept()

    length_data = other_socket.recv(2)
    if not length_data:
        raise ConnectionError("Failed to receive filename length.")
    fileName_length = unpack("!H", length_data)[0]

    fileName_data = other_socket.recv(fileName_length)
    if not fileName_data:
        raise ConnectionError("Failed to receive filename.")
    filename = fileName_data.decode('utf-8')

    size_data = other_socket.recv(8)
    if not size_data:
        raise ConnectionError("Failed to receive file size.")
    fileSize = unpack("!Q", size_data)[0]

    return filename, fileSize

ReceiveFileInfoHeader(info_receiver_socket)

def send_transfer_request(ip, file_path):
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    info_sender_socket.connect((ip, 15556))
    info_sender_socket.send(create_file_info_header(file_name, file_size))
