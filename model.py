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

    class __message_type(Enum):
        TRANSFER_REQUEST = 1
        TRANSFER_ACCEPT = 2
        TRANSFER_REJECT = 3
        TRANSFER_PACKET = 4
        TRANSFER_PAUSE = 5
        TRANSFER_RESUME = 6
        TRANSFER_CANCEL = 7
        TRANSFER_FINISH = 8

    def listen_for_connections(self, listener_socket):
        listener_socket.listen()
        while True:
            other_socket, addr = listener_socket.accept()
            threading.Thread(target=self.__handle_connection, args=(other_socket, addr)).start()

    def __handle_connection(self, socket, addr):
        while True:
            try:
                header = socket.recv(1 + 128 + 4) 
                # | 1 B packet type | 16 B UUID | 4 B (uint) payload length | = Header 133 BYTES

                packet_type, transfer_id, packet_length = struct.unpack('!B16sI', header)
                packet_type = self.__message_type(packet_type)
                packet_payload = socket.recv(packet_length)

                if packet_type == self.__message_type.TRANSFER_REQUEST:
                    packet_payload = json.loads(packet_payload)

                    transfer = {
                        "transfer_id": transfer_id,
                        "ip": addr[0],
                        "file_name": packet_payload["file_name"],
                        "file_size": packet_payload["file_size"],
                        "is_outbound": True,
                        "transfer_speed": 0,
                        "transferred": 0,
                        "path": "",
                        "hash": packet_payload["hash"],
                        "status": self.__message_type.TRANSFER_REQUEST,
                        "pause_condition": threading.Condition(),
                        "file_handle": None,
                    }

                    self.presenter.present_incoming_transfer_request(transfer)

                if packet_type == self.__message_type.TRANSFER_PACKET:
                    transfer[transfer_id]["file_handle"].write(packet_payload)
                    transfer[transfer_id]["transferred"] += len(packet_payload)

                if packet_type == self.__message_type.TRANSFER_PAUSE:
                    self.transfers[transfer_id]["status"] = self.__message_type.TRANSFER_PAUSE
                    self.transfers[transfer_id]["pause_condition"].wait()

                if packet_type == self.__message_type.TRANSFER_RESUME:
                    self.transfers[transfer_id]["status"] = self.__message_type.TRANSFER_RESUME
                    self.transfers[transfer_id]["pause_condition"].notify()

                if packet_type == self.__message_type.TRANSFER_CANCEL:
                    self.transfers[transfer_id]["status"] = self.__message_type.TRANSFER_CANCEL
                    transfer[transfer_id]["file_handle"].close()
                    break

                if packet_type == self.__message_type.TRANSFER_FINISH:
                    self.transfers[transfer_id]["status"] = self.__message_type.TRANSFER_FINISH
                    transfer[transfer_id]["file_handle"].close()
                    break

                    # maybe check hash

            # TODO: more rigorous exception handling
            except Exception as e:
                transfer[transfer_id]["file_handle"].close()
                self.presenter.esception_happened(e)
                break

    def __create_file_info_header_packet(self, file_path):
        """Returns the header and its uuid"""
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

        header = struct.pack("!B16sI", type, uuid, 1, 0) # a payload of length 1, which will be discarded
        return header

    def transfer_file(self, connected_socket, ip, file_path):

        with open(file_path, 'rb') as file:
            while chunk := file.read(8192):
                if ip in active_outbound_transfers:        
                    if active_outbound_transfers[ip][reference_hash]["control_flag"] == self.message_type.TRANSFER_CANCEL:
                        break
                    
                    if active_outbound_transfers[ip][reference_hash]["control_flag"] == self.message_type.TRANSFER_PAUSE:

                        with active_outbound_transfers[ip][reference_hash]["pausing_condition"]:
                            active_outbound_transfers[ip][reference_hash]["pausing_condition"].wait()

                sender_socket.send(chunk)

        if active_outbound_transfers[ip][reference_hash]["control_flag"] == self.message_type.TRANSFER_CANCEL:  
            del active_outbound_transfers[ip][reference_hash]
            if not active_outbound_transfers[ip]:
                del active_outbound_transfers[ip]
        else:
            sender_socket.close()



def initiate_transfer(ip, file_path, queue):
    def transfer_thread():
        sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        response = send_transfer_request(sender_socket, ip, file_path)
        sender_socket.close()
        if response["type"] == self.message_type.TRANSFER_REJECT:
            queue.put(({"type": self.message_type.TRANSFER_REJECT, "ip":ip}, None))
        else:
            sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            file_name = path.basename(file_path)
            file_size = path.getsize(file_path)
            reference_hash = sha1_chunks(file_path)
            add_to_active_outbound_transfers(ip, file_name, file_size, reference_hash, file_path)

            info = {
                "type": self.message_type.TRANSFER_ACCEPT,
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
    info["type"] = self.message_type(info["type"])
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

    if value == self.message_type.TRANSFER_ACCEPT or value == self.message_type.TRANSFER_RESUME:
        dict[ip][reference_hash]["control_flag"] = self.message_type.TRANSFER_PAUSE
    else:
        dict[ip][reference_hash]["control_flag"] = self.message_type.TRANSFER_RESUME
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
        "control_flag": self.message_type.TRANSFER_ACCEPT,
        "pausing_condition": threading.Condition()
    } 

def add_to_active_outbound_transfers(ip, file_name, file_size, hash, file_path):
    if not ip in active_outbound_transfers:
        active_outbound_transfers[ip] = {}
    
    active_outbound_transfers[ip][hash] = {
        "file_name": file_name,
        "file_size": file_size,
        "file_path": file_path,
        "control_flag": self.message_type.TRANSFER_ACCEPT,
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