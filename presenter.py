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
    
    def send_transfer_request(self, destination_ip, file_path, label_index):
        threading.Thread(target=self.model.initiate_transfer, args=(destination_ip, file_path, label_index)).start()

    def toggle_pause_transfer(self, uuid):
        self.model.toggle_transfer_pause(uuid)

    def cancel_transfer(self, uuid):
        self.model.cancel_transfer(uuid)

    def check_for_active_transfers(self):
        return self.model.check_for_active_transfers()

    # Model

    def update_send_request_windows_label(self, label_index, status):
        text = ""
        if status == "hashcalc": text = "Calculating SHA-1 hash..."
        if status == "sendreq": text = "Sending transfer request..."
        self.view.update_status_label(label_index, text)

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

    def __convert_control_flags_to_string(self, control_flag):
        
        if control_flag == self.model._Model__control_flags.TRANSFER_ACCEPT.TRANSFER_ACCEPT:
            return "Transfer accepted"
        if control_flag == self.model._Model__control_flags.TRANSFER_PAUSE.TRANSFER_PAUSE:
            return "Transfer paused"
        if control_flag == self.model._Model__control_flags.TRANSFER_RESUME.TRANSFER_RESUME:
            return "Transfer resumed"
        if control_flag == self.model._Model__control_flags.TRANSFER_CANCEL.TRANSFER_CANCEL:
            return "Transfer cancelled"
        if control_flag == self.model._Model__control_flags.TRANSFER_CANCEL.TRANSFER_FINISH:
            return "Transfer finished"

    def sync_transfers_to_ui(self, transfers):
 
        for uuid, transfer in transfers.items():
            info = {
                "transfer_uuid": transfer["transfer_uuid"],
                "ip": transfer["ip"],
                "file_name": transfer["file_name"],
                "file_size": transfer["file_size"],
                "hash": transfer["hash"],
                "is_outbound": transfer["is_outbound"],
                "transfer_speed": transfer["transfer_speed"],
                "transferred": transfer["transferred"],
                "status": self.__convert_control_flags_to_string(transfer["status"]),
                "display_X": transfer["status"] == self.model._Model__control_flags.TRANSFER_BROKEN or
                    transfer["status"] == self.model._Model__control_flags.TRANSFER_FINISH or
                    transfer["status"] == self.model._Model__control_flags.TRANSFER_CANCEL 
            }
            self.view.sync_transferring_frame_to_ui(info)

    def exception_happened(self, e):
        self.view.create_generic_popup(e, "An exception occured")

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

