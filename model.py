import threading, json, socket, struct, time
from os import path
from misc import sha1_chunks
from enum import Enum
from uuid import UUID, uuid4

class Model:
    def __init__(self, presenter, remote_port = 15555, local_port = 15555):
        self.presenter = presenter
        self.remote_port = remote_port
        self.local_port = local_port
        self.__transfers = {}
        self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener_socket.setblocking(True)
        self.listener_socket.bind(("0.0.0.0", local_port))

    class __control_flags(Enum):
        TRANSFER_REQUEST = 1
        TRANSFER_ACCEPT = 2
        TRANSFER_REJECT = 3
        TRANSFER_PACKET = 4
        TRANSFER_PAUSE = 5
        TRANSFER_RESUME = 6
        TRANSFER_CANCEL = 7
        TRANSFER_FINISH = 8
        # TRANSFER_BROKEN = 9

    def __recv_all(self, socket, size):
        data = b""
        while len(data) < size:
            chunk = socket.recv(size - len(data))
            if not chunk:
                raise ConnectionError("Socket connection closed before all data was received")
            data += chunk
        return data

    def __add_transfer(self, uuid, ip, file_name, file_size, file_hash, is_outbound, socket, file_path=""):
        transfer = {
            "transfer_uuid": uuid,
            "ip": ip,
            "file_name": file_name,
            "file_size": file_size,
            "is_outbound": is_outbound,
            "transfer_speed": 0,
            "transferred": 0,
            "path": file_path,
            "hash": file_hash,
            "status": self.__control_flags.TRANSFER_REQUEST,
            "socket": socket,
            "pause_condition": threading.Condition(),
            "file_handle": None,
            "watched": True
        }

        self.__transfers[uuid] = transfer

    def __listen_for_connections(self):
        self.listener_socket.listen()
        while True:
            other_socket, addr = self.listener_socket.accept()
            threading.Thread(target=self.__handle_incoming_messages, args=(other_socket, addr)).start()

    def __decode_packet(self, socket):
        """Returns packet_type, transfer_uuid, packet_payload"""
        # | 1 B packet type | 16 B UUID | 4 B (uint) payload length | = Header 133 BYTES
        packet = self.__recv_all(socket, 1 + 16 + 4) 
        packet_type, transfer_uuid, payload_length = struct.unpack('!B16sI', packet)
        transfer_uuid = UUID(bytes=transfer_uuid)
        packet_type = self.__control_flags(packet_type)
        packet_payload = self.__recv_all(socket, payload_length)

        if not packet_type == self.__control_flags.TRANSFER_PACKET and payload_length != 0:
            packet_payload = json.loads(packet_payload.decode('utf-8'))

        return packet_type, transfer_uuid, packet_payload

    def __handle_incoming_messages(self, connected_socket, addr):
        """A generic function for handling the reception of all types of packets"""
        while True:
            packet_type, transfer_uuid, packet_payload = self.__decode_packet(connected_socket)
            if packet_type == self.__control_flags.TRANSFER_REQUEST:

                self.__add_transfer(transfer_uuid, addr[0], packet_payload["file_name"], packet_payload["file_size"], packet_payload["hash"], False, connected_socket)

                self.presenter.present_incoming_transfer_request(self.__transfers[transfer_uuid])
            
            if packet_type == self.__control_flags.TRANSFER_PACKET:
                self.__transfers[transfer_uuid]["file_handle"].write(packet_payload)
                self.__transfers[transfer_uuid]["transferred"] += len(packet_payload)
                
                if self.__transfers[transfer_uuid]["transferred"] == self.__transfers[transfer_uuid]["file_size"]:
                    finish_packet = self.__create_transfer_control_packet(transfer_uuid, self.__control_flags.TRANSFER_FINISH)
                    connected_socket.send(finish_packet)
                    connected_socket.close()
                    self.__transfers[transfer_uuid]["status"] = self.__control_flags.TRANSFER_FINISH
                    break

            if packet_type == self.__control_flags.TRANSFER_PAUSE:
                self.__transfers[transfer_uuid]["status"] = self.__control_flags.TRANSFER_PAUSE

            if packet_type == self.__control_flags.TRANSFER_RESUME:
                self.__transfers[transfer_uuid]["status"] = self.__control_flags.TRANSFER_RESUME
                if self.__transfers[transfer_uuid]["is_outbound"]:
                    with self.__transfers[transfer_uuid]["pause_condition"]:
                        self.__transfers[transfer_uuid]["pause_condition"].notify()

            if packet_type == self.__control_flags.TRANSFER_CANCEL:
                self.__transfers[transfer_uuid]["status"] = self.__control_flags.TRANSFER_CANCEL
                self.__transfers[transfer_uuid]["file_handle"].close()
                break

            if packet_type == self.__control_flags.TRANSFER_FINISH:
                self.__transfers[transfer_uuid]["status"] = self.__control_flags.TRANSFER_FINISH
                self.__transfers[transfer_uuid]["file_handle"].close()
                break


    def __create_file_info_header_packet(self, file_path):
        """Returns the header, uuid, file_name, file_size, hash"""
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
        header = struct.pack("!B16sI", self.__control_flags.TRANSFER_REQUEST.value, uuid.bytes, len(data)) + data

        return header, uuid, file_name, file_size, file_hash

    def __create_transfer_control_packet(self, uuid, type):
        """Returns the transfer control packet for a uuid"""

        # | 1 B packet type | 16 B UUID | 4 B (uint) payload length | = Header 133 BYTES

        header = struct.pack("!B16sI", type.value, uuid.bytes, 0)
        return header

    def __create_transfer_packet_header(self, uuid, payload_length):
        # | 1 B packet type | 16 B UUID | 4 B (uint) payload length | = Header 133 BYTES

        header = struct.pack("!B16sI", self.__control_flags.TRANSFER_PACKET.value, uuid.bytes, payload_length)
        return header
    
    def __transfer_file(self, connected_socket, uuid, file_path):
        chunk_size = 1024
        with self.__transfers[uuid]["file_handle"] as file:
            while chunk := file.read(chunk_size):
                if self.__transfers[uuid]["status"] == self.__control_flags.TRANSFER_CANCEL:
                    break

                if self.__transfers[uuid]["status"] == self.__control_flags.TRANSFER_PAUSE:
                    with self.__transfers[uuid]["pause_condition"]:
                        self.__transfers[uuid]["pause_condition"].wait()

                header = self.__create_transfer_packet_header(uuid, len(chunk))
                connected_socket.send(header + chunk)
                self.__transfers[uuid]["transferred"] += len(chunk)
                # time.sleep(1)

    def initiate_transfer(self, ip, file_path):

        sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sender_socket.settimeout(60)
        header, uuid, file_name, file_size, file_hash = self.__create_file_info_header_packet(file_path)
        
        self.__add_transfer(uuid, ip, file_name, file_size, file_hash, True, sender_socket, file_path=file_path)

        sender_socket.connect((ip, self.remote_port))
        sender_socket.send(header)

        packet_type, _, _ = self.__decode_packet(sender_socket)
        
        if packet_type == self.__control_flags.TRANSFER_REJECT:
            self.presenter.present_rejected_transfer(self.__transfers[uuid])
            self.__transfers[uuid]["status"] = self.__control_flags.TRANSFER_REJECT
            return
        else:
            sender_socket.setblocking(True)
            self.__transfers[uuid]["status"] = self.__control_flags.TRANSFER_ACCEPT
            self.__transfers[uuid]["file_handle"] = open(file_path, "rb")
            threading.Thread(target=self.__transfer_file, args=(sender_socket, uuid, file_path), daemon=True).start()
            threading.Thread(target=self.__handle_incoming_messages, args=(sender_socket, (ip, self.remote_port)), daemon=True).start()

    def accept_transfer(self, uuid, dir_path):
        accept_packet = self.__create_transfer_control_packet(uuid, self.__control_flags.TRANSFER_ACCEPT)

        self.__transfers[uuid]["status"] = self.__control_flags.TRANSFER_ACCEPT

        file_path = dir_path + "/" + self.__transfers[uuid]["file_name"]
        self.__transfers[uuid]["path"] = file_path
        self.__transfers[uuid]["file_handle"] = open(file_path, "wb")

        self.__transfers[uuid]["socket"].send(accept_packet)

    def reject_transfer(self, uuid):
        reject_packet = self.__create_transfer_control_packet(uuid, self.__control_flags.TRANSFER_REJECT)
        self.__transfers[uuid]["status"] = self.__control_flags.TRANSFER_REJECT
        self.__transfers[uuid]["socket"].send(reject_packet)

    def cancel_transfer(self, uuid):
        cancel_packet = self.__create_transfer_control_packet(uuid, self.__control_flags.TRANSFER_CANCEL)
        self.__transfers[uuid]["status"] = self.__control_flags.TRANSFER_CANCEL
        self.__transfers[uuid]["socket"].send(cancel_packet)

    def toggle_transfer_pause(self, uuid):
        if self.__transfers[uuid]["status"] == self.__control_flags.TRANSFER_ACCEPT or self.__transfers[uuid]["status"] == self.__control_flags.TRANSFER_RESUME:
            self.__transfers[uuid]["status"] = self.__control_flags.TRANSFER_PAUSE
            pause_packet = self.__create_transfer_control_packet(uuid, self.__control_flags.TRANSFER_PAUSE)
            self.__transfers[uuid]["socket"].send(pause_packet)
        else:
            self.__transfers[uuid]["status"] = self.__control_flags.TRANSFER_RESUME
            resume_packet = self.__create_transfer_control_packet(uuid, self.__control_flags.TRANSFER_RESUME)
            self.__transfers[uuid]["socket"].send(resume_packet)
            if self.__transfers[uuid]["is_outbound"]:
                with self.__transfers[uuid]["pause_condition"]:
                    self.__transfers[uuid]["pause_condition"].notify()

    def __get_active_transfers(self):
        watched_transfers = {
            key: value
            for key, value in self.__transfers.items()
            if value["status"] != self.__control_flags.TRANSFER_REQUEST and
            value["status"] != self.__control_flags.TRANSFER_REJECT and
            value["watched"]
        }
        return watched_transfers

    def __get_transferred_amounts(self):
        active_transfers = self.__get_active_transfers()
        amounts = {
            key: value["transferred"]
            for key, value in active_transfers.items()
        }
        return amounts

    def update_transfer_info(self):
        interval = 0.1

        old_query = self.__get_transferred_amounts()
        while True:
            new_query = self.__get_transferred_amounts()

            active_transfers = self.__get_active_transfers()
            to_show = {}

            for uuid, transfer in active_transfers.items():
                to_show[uuid] = self.__transfers[uuid]
                if(old_query.get(uuid)):
                    data_difference = new_query[uuid] - old_query[uuid]
                    speed = data_difference / interval
                    self.__transfers[uuid]["transfer_speed"] = speed
                    
                    if transfer["status"] == self.__control_flags.TRANSFER_FINISH:
                        self.__transfers[uuid]["watched"] = False
                        self.__transfers[uuid]["transfer_speed"] = 0

            old_query = new_query

            self.presenter.sync_transfers_to_ui(to_show)
            time.sleep(interval)
        
    def launch(self):
        threading.Thread(target=self.__listen_for_connections, daemon=True).start()
        threading.Thread(target=self.update_transfer_info, daemon=True).start()