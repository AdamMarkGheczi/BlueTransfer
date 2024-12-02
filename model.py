import threading, json, socket, struct
from os import path
from misc import sha1_chunks
from enum import Enum
from uuid import uuid4

class Model:
    def __init__(self, presenter, port = 15556):
        self.presenter = presenter
        self.port = port
        self.transfers = {}
        self.transfer_id = 0
        self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener_socket.setblocking(True)
        self.listener_socket.bind(("0.0.0.0", port))

    class __message_type(Enum):
        TRANSFER_REQUEST = 1
        TRANSFER_ACCEPT = 2
        TRANSFER_REJECT = 3
        TRANSFER_PACKET = 4
        TRANSFER_PAUSE = 5
        TRANSFER_RESUME = 6
        TRANSFER_CANCEL = 7
        TRANSFER_FINISH = 8

    def __add_transfer(self, uuid, ip, file_name, file_size, file_hash):
        transfer = {
            "transfer_id": uuid,
            "ip": ip,
            "file_name": file_name,
            "file_size": file_size,
            "is_outbound": True,
            "transfer_speed": 0,
            "transferred": 0,
            "path": "",
            "hash": file_hash,
            "status": self.__message_type.TRANSFER_REQUEST,
            "socket": socket,
            "pause_condition": threading.Condition(),
            "file_handle": None,
        }

        self.transfers[uuid] = transfer

    def listen_for_connections(self, listener_socket):
        listener_socket.listen()
        while True:
            other_socket, addr = listener_socket.accept()
            threading.Thread(target=self.__responde_to_messages, args=(other_socket, addr)).start()

    def __decode_packet(self, socket):
        """Returns packet_type, transfer_id, packet_payload"""
        # | 1 B packet type | 16 B UUID | 4 B (uint) payload length | = Header 133 BYTES
        packet = socket.recv(1 + 128 + 4) 
        packet_type, transfer_id, payload_length = struct.unpack('!B16sI', packet)
        packet_type = self.__message_type(packet_type)
        packet_payload = socket.recv(payload_length)

        return packet_type, transfer_id, packet_payload

    def __responde_to_messages(self, connected_socket, addr):
        """A generic function for handling the reception of all types of packets"""
        while True:
            try:
                packet_type, transfer_id, packet_payload = self.__decode_packet(connected_socket)

                if packet_type == self.__message_type.TRANSFER_REQUEST:
                    packet_payload = json.loads(packet_payload)

                    self.__add_transfer(transfer_id, addr[0], packet_payload["file_name"], packet_payload["file_size"], packet_payload["file_has"])

                    self.presenter.present_incoming_transfer_request(self.transfers[transfer_id])
                
                if packet_type == self.__message_type.TRANSFER_PACKET:
                    self.transfers[transfer_id]["file_handle"].write(packet_payload)
                    self.transfers[transfer_id]["transferred"] += len(packet_payload)

                if packet_type == self.__message_type.TRANSFER_PAUSE:
                    self.transfers[transfer_id]["status"] = self.__message_type.TRANSFER_PAUSE

                if packet_type == self.__message_type.TRANSFER_RESUME:
                    self.transfers[transfer_id]["status"] = self.__message_type.TRANSFER_RESUME
                    self.transfers[transfer_id]["pause_condition"].notify()

                if packet_type == self.__message_type.TRANSFER_CANCEL:
                    self.transfers[transfer_id]["status"] = self.__message_type.TRANSFER_CANCEL
                    self.transfers[transfer_id]["file_handle"].close()
                    break

                if packet_type == self.__message_type.TRANSFER_FINISH:
                    self.transfers[transfer_id]["status"] = self.__message_type.TRANSFER_FINISH
                    self.transfers[transfer_id]["file_handle"].close()
                    break

                    # maybe check hash

            # TODO: more rigorous exception handling
            except Exception as e:
                self.transfers[transfer_id]["file_handle"].close()
                self.presenter.esception_happened(e)
                break

    def __create_file_info_header_packet(self, file_path):
        """Returns the header, uuid, file_name, file_size, file_hash"""
        file_name = path.basename(file_path)
        file_size = path.getsize(file_path)
        file_hash = sha1_chunks(file_path)

        # | 1 B packet type | 16 B UUID | 4 B (uint) payload length | = Header 133 BYTES

        data = {
            "file_name": file_name,
            "file_size": file_size,
            "hash": file_hash
        }

        uuid = uuid4()

        data = json.dumps(data).encode("utf-8")
        header = struct.pack("!B16sI", self.__message_type.TRANSFER_REQUEST, uuid, len(data), data)

        return header, uuid

    def __create_transfer_control_packet(self, uuid, type):
        """Returns the transfer control packet for a uuid"""

        # | 1 B packet type | 16 B UUID | 4 B (uint) payload length | = Header 133 BYTES

        header = struct.pack("!B16sI", type, uuid, 0)
        return header

    def __create_transfer_packet_header(self, uuid, payload_length):
        # | 1 B packet type | 16 B UUID | 4 B (uint) payload length | = Header 133 BYTES

        header = struct.pack("!B16sI", type, uuid, payload_length)
        return header
    
    def __transfer_file(self, connected_socket, uuid, file_path):
        chunk_size = 4096
        header = self.__create_transfer_packet_header(uuid, chunk_size)
        with open(file_path, 'rb') as file:
            while chunk := file.read(chunk_size):
                if self.transfers[uuid]["status"] == self.__message_type.TRANSFER_CANCEL:
                    break

                if self.transfers[uuid]["staus"] == self.message_type.TRANSFER_PAUSE:
                    self.transfers[uuid]["pause_condition"].wait()

                connected_socket.send(header + chunk)
                self.transfers[uuid]["transferred"] += len(chunk)

    def initiate_transfer(self, ip, file_path):

        sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sender_socket.settimeout(60)
        header, uuid, file_name, file_size, file_hash = self.__create_file_info_header_packet(file_path)
        
        self.__add_transfer(uuid, ip, file_name, file_size, file_hash)

        sender_socket.connect((ip, self.port))
        sender_socket.send(header)

        packet_type, _, _ = self.__decode_packet(sender_socket)
        
        if packet_type == self.message_type.TRANSFER_REJECT:
            self.presenter.present_rejected_transfer()
            return
        else:
            threading.Thread(target=self.__transfer_file, args=(sender_socket, uuid, file_path), daemon=True).start()
            threading.Thread(target=self.__responde_to_messages, args=(sender_socket, (ip, self.port)), daemon=True).start()

    def accept_transfer(self, uuid):
        accept_packet = self.__create_transfer_control_packet(uuid, self.__message_type.TRANSFER_ACCEPT)
        self.transfers[uuid]["status"] = self.__message_type.TRANSFER_ACCEPT
        self.transfers[uuid]["socket"].send(accept_packet)

    def cancel_transfer(self, uuid):
        cancel_packet = self.__create_transfer_control_packet(uuid, self.__message_type.TRANSFER_CANCEL)
        self.transfers[uuid]["status"] = self.__message_type.TRANSFER_CANCEL
        self.transfers[uuid]["socket"].send(cancel_packet)

    def toggle_transfer_pause(self, uuid):
        if self.transfers[uuid]["status"] == self.__message_type.TRANSFER_ACCEPT or self.transfers[uuid]["status"] == self.message_type.TRANSFER_RESUME:
            self.transfers[uuid]["status"] = self.message_type.TRANSFER_PAUSE
        else:
            self.transfers[uuid]["status"] = self.message_type.TRANSFER_RESUME
            self.transfers[uuid]["status"].notify()

    def launch(self):
        threading.Thread(target=self.listen_for_connections, args=(self.listener_socket), daemon=True).start()