import socket
from struct import unpack


def ReceiveFileInfoHeader(socket):
    length_data = socket.recv(2)
    if not length_data:
        raise ConnectionError("Failed to receive filename length.")
    fileName_length = unpack("!H", length_data)[0]

    fileName_data = socket.recv(fileName_length)
    if not fileName_data:
        raise ConnectionError("Failed to receive filename.")
    filename = fileName_data.decode('utf-8')

    size_data = socket.recv(8)
    if not size_data:
        raise ConnectionError("Failed to receive file size.")
    fileSize = unpack("!Q", size_data)[0]

    return filename, fileSize


r = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
r.bind(("localhost", 15555))
r.listen()

sender, addr = r.accept()

fileName, fileSize = ReceiveFileInfoHeader(sender)

print(fileName, ' ', fileSize)
