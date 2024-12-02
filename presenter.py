import model, view

class Presenter:
    def __init__(self):
        self.view = view.TransferApp(self)
        self.model = model.Model(self)
        
    # View
    def accept_inbound_transfer(info):
        pass

    def reject_inbound_transfer(info):
        pass
    
    def send_transfer_request(self, destination_ip, file_path):
        pass

    def toggle_pause_transfer(self, info):
        pass

    def cancel_transfer(self, info):
        pass

    # Model

    def present_incoming_transfer_request(self, packet_payload):
        info = {
            "transfer_id": packet_payload["transfer_id"],
            "ip": packet_payload["ip"],
            "file_name": packet_payload["file_name"],
            "file_size": packet_payload["file_size"],
            "hash": packet_payload["hash"]
        }

        self.view.create_transfer_request_popup(info)

    def querry_transfer_statuses(self):
        pass

    def exception_happened(self, e):
        pass

    def launch(self):
        self.view.launch()

presenterInstance = Presenter()
presenterInstance.launch()