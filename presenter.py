import model, view, threading
from os import path

import sys


class Presenter:
    def __init__(self, title, rp, lp):
        self.view = view.TransferApp(title, self)
        self.model = model.Model(self, remote_port=rp, local_port=lp)
        
    # View
    def accept_inbound_transfer(self, uuid, dir_path):
        self.model.accept_transfer(uuid, dir_path)

    def reject_inbound_transfer(self, uuid):
        self.model.reject_transfer(uuid)
    
    def send_transfer_request(self, destination_ip, file_path):
        # threading.Thread(target=self.model.initiate_transfer, args=(destination_ip, file_path)).start()
        self.model.initiate_transfer(destination_ip, file_path)

    def toggle_pause_transfer(self, uuid):
        self.model.toggle_transfer_pause(uuid)

    def cancel_transfer(self, uuid):
        self.model.cancel_transfer(uuid)

    # Model
    def present_incoming_transfer_request(self, transfer):
        info = {
            "transfer_uuid": transfer["transfer_uuid"],
            "ip": transfer["ip"],
            "file_name": transfer["file_name"],
            "file_size": transfer["file_size"],
            "hash": transfer["hash"]
        }

        self.view.create_transfer_request_popup(info)

    def present_rejected_transfer(self, transfer):
        message = f"{transfer["ip"]} has rejected your transfer for {path.basename(transfer["path"])}"
        self.view.create_generic_popup(message)

    def convert_control_flags_to_string(self, control_flag):
        if control_flag == self.model.__control_flags.TRANSFER_ACCEPT:
            return "Transfer accepted"
        if control_flag == self.model.__control_flags.TRANSFER_PAUSE:
            return "Transfer paused"
        if control_flag == self.model.__control_flags.TRANSFER_RESUME:
            return "Transfer resumed"
        if control_flag == self.model.__control_flags.TRANSFER_CANCEL:
            return "Transfer cancelled"

    def sync_transfers_to_ui(self, transfers):
        for uuid, transfer in transfers.items():
            info = {
                "transfer_uuid": transfer["transfer_uuid"],
                "ip": transfer["ip"],
                "file_name": transfer["file_name"],
                "file_size": transfer["file_size"],
                "hash": transfer["hash"],
                "transfer_speed": transfer["transfer_speed"],
                "transferred": transfer["transferred"],
                "status": self.convert_control_flags_to_string(transfer["status"]),
            }
            self.view.sync_transferring_frame_to_ui(info)

    def exception_happened(self, e):
        pass

    def launch(self):
        self.model.launch()
        self.view.launch()


if len(sys.argv) > 1:
    local_port = sys.argv[1]
    remote_port = sys.argv[2]
    title= sys.argv[3]
    BlueTransfer = Presenter(title, int(remote_port), int(local_port))
    BlueTransfer.launch()
else:
    BlueTransfer = Presenter()
    BlueTransfer.launch()

